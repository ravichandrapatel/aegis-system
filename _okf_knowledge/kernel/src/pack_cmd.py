"""Prompt Pack assembly and lookup/pack CLIs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.cards import extract_prompt_card
from src.config import _tiktoken_encoder, count_tokens, load_okf_config
from src.lookup import (
    entries_from_vault,
    load_card_cache,
    load_index,
    load_index_bundle,
    lookup,
)
from src.models import Hit
from src.paths import (
    BRAIN_ROOT,
    DEFAULT_MAX_CARDS,
    DEFAULT_TOKEN_BUDGET,
    INDEX_FORMAT_VERSION,
    VAULT_ROOT,
)

def _card_for(hit: Hit, cache: dict[str, str]) -> str | None:
    """
    intent: Resolve Prompt Card from cache or by reading the markdown file.
    input: hit; optional card cache.
    output: card body or None.
    role: card resolver.
    side_effects: may read one markdown file on cache miss.
    """
    cached = cache.get(hit.entry.concept_id)
    if cached:
        return cached
    path = hit.entry.path
    if path is None or not path.is_file():
        path = VAULT_ROOT / f"{hit.entry.concept_id}.md"
    if not path.is_file():
        return None
    return extract_prompt_card(path.read_text(encoding="utf-8"))

def _query_matches_pack_force(query: str, keywords: list[str]) -> bool:
    """True when any pack_force_when keyword appears as a phrase in the query."""
    if not keywords:
        return False
    q = (query or "").lower()
    for kw in keywords:
        k = kw.lower().strip()
        if k and k in q:
            return True
    return False

def _force_hits_for_query(query: str, type_filter: str | None = None) -> list[Hit]:
    """
    intent: Force-include index entries whose pack_force_when matches the query.
    AGENTS.md: pack/lookup force-includes matching concepts over live rediscovery.
    """
    entries = load_index()
    if entries is None:
        entries = entries_from_vault()
    forced: list[Hit] = []
    seen: set[str] = set()
    for entry in entries:
        if type_filter and entry.ctype.lower() != type_filter.lower():
            continue
        if not _query_matches_pack_force(query, entry.pack_force_when):
            continue
        if entry.concept_id in seen:
            continue
        seen.add(entry.concept_id)
        forced.append(
            Hit(
                entry=entry,
                score=10_000,
                matched=["pack_force_when"],
                graph_hops=None,
            )
        )
    return forced

def assemble_prompt_pack(
    query: str,
    *,
    limit: int = 5,
    type_filter: str | None = None,
    max_cards: int | None = None,
    budget: int | None = None,
) -> tuple[list[dict[str, object]], list]:
    """
    intent: Shared Prompt Pack builder for lookup --card and pack.
    output: (pack rows, raw hits). Each row: id, score, kind, text, tokens.
    Force-includes concepts with matching pack_force_when before ranked hits.
    """
    cfg = load_okf_config()
    max_cards = int(max_cards if max_cards is not None else cfg.get("max_cards", DEFAULT_MAX_CARDS))
    budget = int(budget if budget is not None else cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))
    ranked = lookup(query, limit=limit, type_filter=type_filter)
    forced = _force_hits_for_query(query, type_filter=type_filter)
    # Force-include first, then ranked (dedupe by concept_id).
    merged: list[Hit] = []
    seen_ids: set[str] = set()
    for hit in forced + list(ranked or []):
        cid = hit.entry.concept_id
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        merged.append(hit)
    hits = merged
    if not hits:
        return [], []
    cache = load_card_cache()
    pack: list[dict[str, object]] = []
    used = 0
    for hit in hits:
        if len(pack) >= max(1, max_cards):
            break
        card = _card_for(hit, cache)
        if card:
            kind = "card"
            body = f"### Card: {hit.entry.concept_id}.md (score={hit.score})\n{card}"
        else:
            kind = "stub"
            body = (
                f"### Path: _okf_knowledge/{hit.entry.concept_id}.md "
                f"(score={hit.score})\n"
                f"(no ## Prompt Card — open file only if needed)"
            )
        cost = count_tokens(body)
        if pack and used + cost > budget:
            break
        pack.append(
            {
                "id": hit.entry.concept_id,
                "path": hit.entry.concept_id + ".md",
                "type": hit.entry.ctype,
                "title": hit.entry.title,
                "score": hit.score,
                "kind": kind,
                "text": body,
                "tokens": cost,
            }
        )
        used += cost
    return pack, hits

def _cdata(text: str) -> str:
    """
    intent: Embed text in XML CDATA without breakout on ]]> sequences.
    input: raw text (may contain ]]> ).
    output: CDATA markup safe for XML parsers.
    """
    # Standard split: "]]>" → "]]]]><![CDATA[>" so no section contains terminator.
    safe = str(text).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe}]]>"


def format_pack(pack: list[dict[str, object]], style: str, query: str) -> str:
    """Render Prompt Pack as markdown | json | xml (cards only — never full vault)."""
    total = sum(int(r["tokens"]) for r in pack)
    style = (style or "markdown").lower()
    if style == "json":
        return json.dumps(
            {
                "query": query,
                "token_estimator": "tiktoken:cl100k_base" if _tiktoken_encoder() else "heuristic",
                "total_tokens": total,
                "cards": [
                    {
                        "id": r["id"],
                        "path": r["path"],
                        "type": r["type"],
                        "title": r["title"],
                        "score": r["score"],
                        "kind": r["kind"],
                        "tokens": r["tokens"],
                        "text": r["text"],
                    }
                    for r in pack
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    if style == "xml":
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<okf_prompt_pack>",
            f"  <query>{_xml_esc(query)}</query>",
            f"  <total_tokens>{total}</total_tokens>",
        ]
        for r in pack:
            lines.append(
                f'  <card id="{_xml_esc(str(r["id"]))}" tokens="{r["tokens"]}" '
                f'score="{r["score"]}" kind="{_xml_esc(str(r["kind"]))}">'
            )
            lines.append(f"    {_cdata(str(r['text']))}")
            lines.append("  </card>")
        lines.append("</okf_prompt_pack>")
        return "\n".join(lines)
    header = (
        f"# OKF Prompt Pack\nquery: {query!r}\n"
        f"cards: {len(pack)}  total_tokens: {total}\n"
    )
    body = "\n\n".join(str(r["text"]) for r in pack)
    return header + "\n" + body if pack else header + "\n(no cards)\n"

def _xml_esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def cmd_lookup(args: argparse.Namespace) -> int:
    """
    intent: Find concepts; optionally emit budgeted Prompt Cards.
    input: parsed args.
    output: exit 0 if hits; 1 if none / errors.
    role: subcommand.
    side_effects: stdout/stderr only.
    """
    as_json = bool(getattr(args, "json", False))

    if args.card:
        pack, hits = assemble_prompt_pack(
            args.query,
            limit=args.limit,
            type_filter=args.type_filter,
            max_cards=args.max_cards,
            budget=args.budget,
        )
        if not hits:
            print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
            return 1
        if as_json:
            print(format_pack(pack, "json", args.query))
        else:
            # agent-facing: cards only (no pack header) — same as pre-1.2
            print("\n\n".join(str(r["text"]) for r in pack))
        return 0

    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        if as_json:
            print(json.dumps([h.entry.concept_id + ".md" for h in hits], indent=2))
        else:
            for hit in hits:
                print(hit.entry.concept_id + ".md")
        return 0

    if as_json:
        print(
            json.dumps(
                [
                    {
                        "id": h.entry.concept_id,
                        "path": h.entry.concept_id + ".md",
                        "type": h.entry.ctype,
                        "title": h.entry.title,
                        "description": h.entry.description,
                        "score": h.score,
                        "matched": h.matched,
                        "graph_hops": h.graph_hops,
                    }
                    for h in hits
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if (BRAIN_ROOT / "index.json").is_file():
        _, inv = load_index_bundle()
        src = getattr(lookup, "_last_source", None) or f"index.json v{INDEX_FORMAT_VERSION}"
        if inv and str(src).startswith("index"):
            src = f"{src} (inv={len(inv)} tokens)"
    else:
        src = getattr(lookup, "_last_source", None) or "rg|live-vault"
    print(f"# okf lookup  query={args.query!r}  source={src}  vault={VAULT_ROOT}")
    for hit in hits:
        e = hit.entry
        print(f"{hit.score:3d}  [{e.ctype}]  {e.concept_id}")
        print(f"     {e.title} — {e.description}")
        meta = []
        if hit.matched:
            meta.append("matched=" + ",".join(hit.matched))
        if hit.graph_hops is not None:
            meta.append(f"graph={hit.graph_hops} hop")
        if meta:
            print(f"     ({' '.join(meta)})")
    print(
        "\n# Next: python3 okf.py lookup --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
    return 0

def cmd_pack(args: argparse.Namespace) -> int:
    """
    intent: Export a cards-only Prompt Pack (Repomix-like formats, OKF semantics).
    """
    pack, hits = assemble_prompt_pack(
        args.query,
        limit=args.limit,
        type_filter=args.type_filter,
        max_cards=args.max_cards,
        budget=args.budget,
    )
    if not hits:
        print(f"[okf_pack] no hits for: {args.query!r}", file=sys.stderr)
        return 1
    out = format_pack(pack, args.style, args.query)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"[okf_pack] wrote {args.output} ({len(pack)} cards)", file=sys.stderr)
    else:
        print(out)
    return 0

