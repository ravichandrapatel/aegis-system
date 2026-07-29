"""Vault lint / health checks."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.cards import extract_prompt_card
from src.paths import (
    HOUSE_REQUIRED_FIELDS,
    PROMPT_CARD_MAX_CHARS,
    RESERVED_FILENAMES,
    VAULT_ROOT,
)
from src.vault import (
    concept_id_from_path,
    control_plane_filenames,
    extract_links,
    inject_into_aegis_brain,
    is_standard_concept,
    known_types,
    load_vault,
    resolve_link,
)


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

        # -- House schema (AGENTS.md taxonomy, loaded dynamically) --
        ctype = str(c.frontmatter.get("type", ""))
        taxonomy = known_types()
        if ctype and ctype not in taxonomy:
            add("warning", c.concept_id, "DBG-302",
                f"unknown type '{ctype}' (not in AGENTS.md taxonomy)")
        for fld in HOUSE_REQUIRED_FIELDS:
            if not str(c.frontmatter.get(fld, "")).strip():
                add("warning", c.concept_id, "DBG-303",
                    f"missing house-required field '{fld}'")

        # -- Standards Prompt Card gate (path standards/* OR tag `standard`) --
        if is_standard_concept(c):
            card = extract_prompt_card(c.body)
            if card is None:
                add(
                    "error",
                    c.concept_id,
                    "DBG-308",
                    "standard concepts MUST include a non-empty ## Prompt Card section",
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
                if resolved.exists() and resolved.name in control_plane_filenames():
                    continue
                add("warning", c.concept_id, "DBG-305", f"link escapes vault -> {target}")
                continue
            if not resolved.exists():
                add("warning", c.concept_id, "DBG-304", f"broken link -> {target}")
                continue
            linked_ids.add(target_id)

    # Count links from reserved pages so indexed concepts are not false orphans.
    control_names = control_plane_filenames()
    for special in VAULT_ROOT.rglob("*.md"):
        if special.name not in control_names and special.name not in RESERVED_FILENAMES:
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

def build_lint_report() -> dict[str, object]:
    """Build the structured lint report (no filesystem write)."""
    findings, concept_count = collect_findings()
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    return {
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


def cmd_lint(_args: argparse.Namespace | None = None) -> int:
    """
    intent: Print the lint report, embed it into aegis-brain.html (lint-data),
            exit non-zero on errors. Does not write lint.json.
    input: none.
    output: process exit code (0 clean/warnings-only, 1 errors).
    role: subcommand.
    side_effects: rewrites kernel/src/aegis-brain.html lint-data script tag.
    """
    findings, concept_count = collect_findings()
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    print(f"okf lint: {concept_count} concepts checked ({VAULT_ROOT})")
    for f in errors:
        print(f"  ERROR   {f['concept']}: [{f['code']}] {f['message']}")
    for f in warnings:
        print(f"  WARNING {f['concept']}: [{f['code']}] {f['message']}")
    if not findings:
        print("  clean — vault is conformant and healthy")
    print(f"summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    report = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        inject_into_aegis_brain("lint-data", json.dumps(report, indent=2))
    except OSError as exc:
        write_ok = False
        print(f"[DBG-307] could not embed lint into aegis-brain.html: {exc}", file=sys.stderr)
    return 1 if errors or not write_ok else 0

