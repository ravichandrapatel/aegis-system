"""LLM enrich for description/tags/Prompt Card gaps."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from src.cards import extract_prompt_card
from src.models import Concept
from src.paths import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    ENRICH_MAX_BODY_LINES,
    ENRICH_MAX_TAGS,
    ENRICH_MIN_DESC_LEN,
    LLM_REQUEST_TIMEOUT_S,
    PROMPT_CARD_MAX_CHARS,
    VAULT_ROOT,
)
from src.vault import (
    escape_yaml_scalar,
    format_frontmatter,
    is_standard_concept,
    load_vault,
    parse_frontmatter,
)


ENRICH_PROMPT = """\
You are enriching one document of an Aegis OKF knowledge vault so that a
lexical search over frontmatter (title/tags/description) finds it, and so a
slim "Prompt Card" can be injected into coding-agent prompts.

Return a JSON object with exactly these fields (use "" / [] to skip a field):

  "description" - one sentence, <= 120 chars, stating what the document
                  covers, specific enough to rank in keyword search.
  "tags"        - 0-{max_tags} short kebab-case topic tags (purpose/domain,
                  not the type name). Only tags justified by the body.
  "prompt_card" - <= {card_chars} chars of binding MUST / SHOULD / FORBIDDEN
                  lines (or exact commands) an agent needs at generation time.
                  Plain text lines only, no headings, no link lists, no prose
                  essays. Empty string if the document has no binding rules.

Rules:
- Base everything ONLY on the document below; do not invent facts.
- Do not restate the whole document; compress to what an agent must obey.
- Reply with ONLY the JSON object, no markdown fences, no preamble.

Document type: {ctype}
Document id: {concept_id}
Title: {title}
Existing description: {description}
Existing tags: {tags}
Document body:
{body}
"""

def _enrich_needs(concept: Concept) -> list[str]:
    """
    intent: Decide which of the three retrieval fields are missing/weak.
    input: parsed concept.
    output: list of gap names ("description", "tags", "card").
    role: pure gap detector (keeps the pass idempotent).
    side_effects: none.
    """
    gaps: list[str] = []
    desc = str(concept.frontmatter.get("description", "")).strip()
    if len(desc) < ENRICH_MIN_DESC_LEN:
        gaps.append("description")
    tags = concept.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    if len([t for t in tags if str(t).strip()]) < 2:
        gaps.append("tags")
    if extract_prompt_card(concept.body) is None:
        gaps.append("card")
    return gaps

def _truncate_body(body: str, max_lines: int) -> str:
    lines = body.splitlines()
    if len(lines) <= max_lines:
        return body
    return "\n".join(lines[:max_lines] + ["... (truncated)"])

def _llm_chat(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """
    intent: Minimal OpenAI-compatible /chat/completions call via stdlib.
    input: endpoint config; single user prompt.
    output: assistant message content.
    role: transport (replaces okf-generator's openai client dependency).
    side_effects: one HTTPS/HTTP request.
    """
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
    ).encode("utf-8")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    scheme = urlparse(endpoint).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"[DBG-404] LLM endpoint must be http/https, got {scheme!r}")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'no-key'}",
        },
        method="POST",
    )
    # Scheme gated above; stdlib client (local/OpenAI-compatible endpoints).
    with urllib.request.urlopen(req, timeout=LLM_REQUEST_TIMEOUT_S) as resp:  # nosec B310
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"] or "")

def _parse_json_reply(raw: str) -> dict:
    """
    intent: Tolerantly parse the model's JSON-only reply (strip fences).
    input: raw assistant text.
    output: dict (empty on failure).
    role: pure parser.
    side_effects: none.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

def _sanitize_enrich_reply(data: dict) -> dict:
    """
    intent: Shape/length-validate model output before touching vault files.
    input: parsed reply dict.
    output: dict with only safe, clamped fields.
    role: validation boundary (LLM output is untrusted input).
    side_effects: none.
    """
    out: dict = {}
    desc = str(data.get("description", "")).strip().replace("\n", " ")
    if desc:
        out["description"] = desc[:160]
    tags = data.get("tags", [])
    if isinstance(tags, list):
        clean = []
        for t in tags[:ENRICH_MAX_TAGS]:
            t = re.sub(r"[^a-z0-9-]", "", str(t).strip().lower().replace(" ", "-"))
            if 2 <= len(t) <= 40:
                clean.append(t)
        if clean:
            out["tags"] = clean
    card = str(data.get("prompt_card", "")).strip()
    if card:
        out["prompt_card"] = card[:PROMPT_CARD_MAX_CHARS]
    return out

def _apply_enrich(concept: Concept, gaps: list[str], fix: dict) -> tuple[str, list[str]]:
    """
    intent: Produce the updated file text, filling only the detected gaps.
    input: concept; gap names; sanitized fix dict.
    output: (new file text, list of gaps actually filled).
    role: pure rewriter (caller writes the file).
    side_effects: none.
    """
    text = concept.path.read_text(encoding="utf-8")
    filled: list[str] = []

    if "description" in gaps and fix.get("description"):
        new_line = f"description: {fix['description']}"
        if re.search(r"^description:.*$", text, flags=re.M):
            text = re.sub(r"^description:.*$", new_line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(type:.*)$", r"\1\n" + new_line, text, count=1, flags=re.M)
        filled.append("description")

    if "tags" in gaps and fix.get("tags"):
        existing = concept.frontmatter.get("tags", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        merged = [str(t) for t in existing if str(t).strip()]
        for t in fix["tags"]:
            if t not in merged:
                merged.append(t)
        new_line = f"tags: [{', '.join(merged[:ENRICH_MAX_TAGS])}]"
        if re.search(r"^tags:.*$", text, flags=re.M):
            text = re.sub(r"^tags:.*$", new_line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(type:.*)$", r"\1\n" + new_line, text, count=1, flags=re.M)
        filled.append("tags")

    if "card" in gaps and fix.get("prompt_card"):
        block = f"\n## Prompt Card\n\n```text\n{fix['prompt_card']}\n```\n"
        # Insert before the first Related heading so the card stays scoped;
        # otherwise append at the end of the document.
        m = re.search(r"^#{1,2} Related\s*$", text, flags=re.M)
        if m:
            text = text[: m.start()] + block.lstrip("\n") + "\n" + text[m.start():]
        else:
            text = text.rstrip("\n") + "\n" + block
        filled.append("card")

    if filled:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = re.sub(r"^timestamp:.*$", f"timestamp: {stamp}", text, count=1, flags=re.M)
    return text, filled

def cmd_enrich(args: argparse.Namespace) -> int:
    """
    intent: Report gaps; with --write, fill them via the configured LLM.
    input: parsed args.
    output: exit 0 (clean or all fixed), 1 (gaps remain / errors).
    role: subcommand.
    side_effects: --write edits vault markdown; network calls to the LLM.
    """
    targets: list[tuple[Concept, list[str]]] = []
    for concept in load_vault():
        if concept.parse_error:
            continue
        if args.only and args.only not in concept.concept_id:
            continue
        gaps = _enrich_needs(concept)
        if gaps:
            targets.append((concept, gaps))

    if not targets:
        print("okf enrich: no gaps — every concept has description, tags, and a Prompt Card")
        return 0

    print(f"okf enrich: {len(targets)} concept(s) with gaps")
    for concept, gaps in targets:
        print(f"  {concept.concept_id}: missing {', '.join(gaps)}")

    if not args.write:
        print("\n(dry-run — pass --write to fill gaps via the configured LLM)")
        return 1

    base_url = os.environ.get("OKF_LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    api_key = os.environ.get("OKF_LLM_API_KEY", "")
    model = os.environ.get("OKF_LLM_MODEL", DEFAULT_LLM_MODEL)
    print(f"\nokf enrich: endpoint={base_url} model={model}")

    enriched = 0
    skipped = 0
    if args.limit > 0:
        targets = targets[: args.limit]
    for concept, gaps in targets:
        prompt = ENRICH_PROMPT.format(
            max_tags=ENRICH_MAX_TAGS,
            card_chars=PROMPT_CARD_MAX_CHARS,
            ctype=str(concept.frontmatter.get("type", "")),
            concept_id=concept.concept_id,
            title=str(concept.frontmatter.get("title", "")),
            description=str(concept.frontmatter.get("description", "")) or "(none)",
            tags=", ".join(map(str, concept.frontmatter.get("tags", []) or [])) or "(none)",
            body=_truncate_body(concept.body, args.max_body),
        )
        try:
            reply = _llm_chat(base_url, api_key, model, prompt)
        except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
            print(f"  SKIP {concept.concept_id}: LLM call failed ({exc})", file=sys.stderr)
            skipped += 1
            continue
        fix = _sanitize_enrich_reply(_parse_json_reply(reply))
        if not fix:
            print(f"  SKIP {concept.concept_id}: unusable LLM reply", file=sys.stderr)
            skipped += 1
            continue
        text, filled = _apply_enrich(concept, gaps, fix)
        if not filled:
            print(f"  SKIP {concept.concept_id}: nothing usable for {gaps}", file=sys.stderr)
            skipped += 1
            continue
        concept.path.write_text(text, encoding="utf-8")
        enriched += 1
        print(f"  OK   {concept.concept_id}: filled {', '.join(filled)}")

    print(f"\nokf enrich: {enriched} enriched, {skipped} skipped")
    if enriched:
        print("Next (maintain playbook): python3 _okf_knowledge/kernel/okf.py compile "
              "&& python3 _okf_knowledge/kernel/okf.py lint")
    return 0 if skipped == 0 else 1

