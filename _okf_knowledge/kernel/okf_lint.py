#!/usr/bin/env python3
# file_name: okf_lint.py
# description: Health check for the Aegis OKF vault — OKF v0.1 conformance
#              (errors) plus broken links, orphans, schema drift (warnings),
#              and the standards Prompt Card gate (ADR follow-up #3).
#              Writes lint.json at the vault root for aegis-brain.
# version: 0.4.0
# authors: contributors
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from okf_common import (
    BRAIN_ROOT,
    CONTROL_PLANE_FILES,
    NON_CONCEPT_FILES,
    VAULT_ROOT,
    concept_id_from_path,
    extract_links,
    inject_into_aegis_brain,
    load_vault,
    resolve_link,
)
from prompt_card import extract_prompt_card

# Taxonomy from AGENTS.md — drift is a warning, not an error (OKF tolerates unknown types).
# Vault taxonomy (Zone 4) + kernel execution types (Zone 2). Keep them distinct
# so vendor/module docs do not collide with passive vault Concepts/Systems.
KNOWN_TYPES = {
    "Concept",
    "Playbook",
    "System",
    "Reference",
    "Incident",
    "Module",
    "Vendor",
}
HOUSE_REQUIRED_FIELDS = ("title", "description")
# Rule #2 target: ≤150 tokens ≈ 600 characters (see prompt_card.py --max-chars).
PROMPT_CARD_MAX_CHARS = 600


def collect_findings() -> tuple[list[dict[str, str]], int]:
    """
    intent: Run every check and return structured findings.
    input: none (reads vault from disk).
    output: (findings, concept_count) — each finding has severity/concept/code/message.
    role: core checker, shared by the CLI report and lint.json.
    side_effects: none (read-only).
    """
    concepts = load_vault()
    findings: list[dict[str, str]] = []
    linked_ids: set[str] = set()
    ids = {c.concept_id for c in concepts}

    def add(severity: str, concept: str, code: str, message: str) -> None:
        findings.append(
            {"severity": severity, "concept": concept, "code": code, "message": message}
        )

    for c in concepts:
        # -- Conformance (OKF v0.1 §9) --
        if c.parse_error is not None:
            code = c.parse_error.split("]", 1)[0].lstrip("[")
            add("error", c.concept_id, code, c.parse_error)
            continue
        if not str(c.frontmatter.get("type", "")).strip():
            add("error", c.concept_id, "DBG-301", "missing required 'type' field")

        # -- House schema (AGENTS.md) --
        ctype = str(c.frontmatter.get("type", ""))
        if ctype and ctype not in KNOWN_TYPES:
            add("warning", c.concept_id, "DBG-302",
                f"unknown type '{ctype}' (not in AGENTS.md taxonomy)")
        for fld in HOUSE_REQUIRED_FIELDS:
            if not str(c.frontmatter.get(fld, "")).strip():
                add("warning", c.concept_id, "DBG-303",
                    f"missing house-required field '{fld}'")

        # -- Standards Prompt Card gate (ADR follow-up #3 / Rule #2) --
        # Binding house law under standards/* MUST expose a non-empty ## Prompt Card.
        if c.concept_id.startswith("standards/"):
            card = extract_prompt_card(c.body)
            if card is None:
                add(
                    "error",
                    c.concept_id,
                    "DBG-308",
                    "standards/* MUST include a non-empty ## Prompt Card section",
                )
            elif len(card) > PROMPT_CARD_MAX_CHARS:
                add(
                    "warning",
                    c.concept_id,
                    "DBG-309",
                    f"Prompt Card is {len(card)} chars "
                    f"(target ≤{PROMPT_CARD_MAX_CHARS} ≈150 tokens)",
                )

        # -- Links --
        for target in extract_links(c.body):
            resolved = resolve_link(target, c.path)
            target_id = concept_id_from_path(resolved)
            if target_id is None:
                # Control-plane files may live at the share/repo root (parent).
                if resolved.exists() and resolved.name in CONTROL_PLANE_FILES:
                    continue
                add("warning", c.concept_id, "DBG-305", f"link escapes vault -> {target}")
                continue
            if not resolved.exists():
                add("warning", c.concept_id, "DBG-304", f"broken link -> {target}")
                continue
            linked_ids.add(target_id)

    # Count links from reserved pages so indexed concepts are not false orphans.
    for special in VAULT_ROOT.rglob("*.md"):
        if special.name not in NON_CONCEPT_FILES:
            continue
        try:
            body = special.read_text(encoding="utf-8")
        except OSError:
            continue
        for target in extract_links(body):
            resolved = resolve_link(target, special)
            target_id = concept_id_from_path(resolved)
            if target_id is not None and resolved.exists():
                linked_ids.add(target_id)

    for orphan in sorted(ids - linked_ids):
        add(
            "warning",
            orphan,
            "DBG-306",
            "orphan — no inbound links from concepts or reserved pages",
        )

    return findings, len(concepts)


def main() -> int:
    """
    intent: Print the lint report, write lint.json (also embedded into
            aegis-brain.html for file:// auto-load), exit non-zero on errors.
    input: none.
    output: process exit code (0 clean/warnings-only, 1 errors).
    role: CLI entry point.
    side_effects: writes lint.json at the vault root; rewrites aegis-brain.html.
    """
    findings, concept_count = collect_findings()
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    print(f"okf_lint: {concept_count} concepts checked ({VAULT_ROOT})")
    for f in errors:
        print(f"  ERROR   {f['concept']}: [{f['code']}] {f['message']}")
    for f in warnings:
        print(f"  WARNING {f['concept']}: [{f['code']}] {f['message']}")
    if not findings:
        print("  clean — vault is conformant and healthy")
    print(f"summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    report = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Package-relative label only — never embed absolute machine paths.
        "vault": VAULT_ROOT.name,
        "summary": {
            "concepts": concept_count,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "findings": findings,
    }
    write_ok = True
    try:
        report_json = json.dumps(report, indent=2)
        (BRAIN_ROOT / "lint.json").write_text(report_json + "\n", encoding="utf-8")
        inject_into_aegis_brain("lint-data", report_json)
    except OSError as exc:
        write_ok = False
        # _log("[T-01] lint.json write failed")
        print(f"[DBG-307] could not write lint.json: {exc}", file=sys.stderr)
    return 1 if errors or not write_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
