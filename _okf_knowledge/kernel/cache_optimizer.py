#!/usr/bin/env python3
# file_name: cache_optimizer.py
# description: Enrich and normalize cached Reference concepts only (frontmatter
#              completeness, tag hygiene), refresh Reference indexes, then
#              trigger graph_compiler (graph.json). NEVER rewrites Playbooks/Systems/Concepts.
# version: 0.3.0
# authors: contributors
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import graph_compiler
from okf_common import VAULT_ROOT, format_frontmatter, load_concept

VAULT_DIR = VAULT_ROOT / "vault"
# Cached upstream dumps land here (or in domain cache dirs that only hold References).
REFERENCE_CACHE_DIRS = {"references", "github-actions"}


def _is_reference(path: Path) -> bool:
    """
    intent: Gate optimizer mutations to Reference concepts only.
    input: path — candidate .md file under vault/.
    output: True when frontmatter type is Reference.
    role: collision guard vs Playbook/System/Concept/Incident.
    side_effects: none (read-only).
    """
    concept = load_concept(path)
    if concept.parse_error is not None:
        return False
    return str(concept.frontmatter.get("type", "")).strip() == "Reference"


def normalize_reference(path: Path) -> list[str]:
    """
    intent: Ensure one cached reference has complete, normalized frontmatter.
    input: path — reference .md file.
    output: list of fixes applied (empty if already clean).
    role: normalizer.
    side_effects: may rewrite the file in place.
    """
    concept = load_concept(path)
    if concept.parse_error is not None:
        return [f"SKIP unparseable: {concept.parse_error}"]
    if str(concept.frontmatter.get("type", "")).strip() != "Reference":
        return []

    fm = dict(concept.frontmatter)
    fixes: list[str] = []
    if not str(fm.get("title", "")).strip():
        fm["title"] = path.stem.replace("-", " ").title()
        fixes.append("derived title from filename")
    if not str(fm.get("description", "")).strip():
        fm["description"] = "Cached upstream documentation."
        fixes.append("added default description")
    if not str(fm.get("timestamp", "")).strip():
        fm["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        fixes.append("stamped timestamp")
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        stripped = [str(t).strip() for t in tags if str(t).strip()]
        normalized = sorted({s.lower() for s in stripped})
        needs_fix = (
            len(stripped) != len({s.lower() for s in stripped})
            or any(s != s.lower() for s in stripped)
            or [s.lower() for s in stripped] != normalized
        )
        if needs_fix:
            fm["tags"] = normalized
            fixes.append("deduped/sorted tags")

    if fixes:
        path.write_text(format_frontmatter(fm) + concept.body, encoding="utf-8")
    return fixes


def rebuild_references_index() -> int:
    """
    intent: Regenerate indexes only for Reference cache directories.
    input: none (reads vault/ tree).
    output: number of index files written.
    role: index generator scoped to avoid colliding with Playbook/System indexes.
    side_effects: writes index.md under Reference cache dirs only.
    """
    if not VAULT_DIR.is_dir():
        return 0
    written = 0
    for source_dir in sorted(p for p in VAULT_DIR.iterdir() if p.is_dir()):
        if source_dir.name not in REFERENCE_CACHE_DIRS:
            continue
        entries = []
        for ref in sorted(source_dir.glob("*.md")):
            if ref.name == "index.md":
                continue
            if not _is_reference(ref):
                continue
            c = load_concept(ref)
            title = c.frontmatter.get("title", ref.stem)
            desc = c.frontmatter.get("description", "")
            source_url = str(c.frontmatter.get("source_url", "")).strip()
            official = f" — [official docs]({source_url})" if source_url else ""
            entries.append(f"* [{title}]({ref.name}) - {desc}{official}")
        if entries:
            body = f"# Cached references — {source_dir.name}\n\n" + "\n".join(entries) + "\n"
            (source_dir / "index.md").write_text(body, encoding="utf-8")
            written += 1
    return written


def main() -> int:
    """
    intent: CLI entry point — normalize References only, rebuild their indexes, recompile.
    input: none.
    output: process exit code.
    role: CLI entry point.
    side_effects: rewrites Reference files + their indexes; runs graph_compiler.
    """
    if not VAULT_DIR.exists():
        print("[DBG-501] no vault/ directory; nothing to optimize", file=sys.stderr)
        return 0
    total_fixes = 0
    for path in sorted(VAULT_DIR.rglob("*.md")):
        if path.name == "index.md":
            continue
        if not _is_reference(path):
            continue
        fixes = normalize_reference(path)
        for fix in fixes:
            print(f"  {path.relative_to(VAULT_ROOT)}: {fix}")
        total_fixes += len(fixes)
    indexes = rebuild_references_index()
    print(f"[DBG-500] {total_fixes} fix(es) applied, {indexes} index(es) rebuilt")
    return graph_compiler.main()


if __name__ == "__main__":
    raise SystemExit(main())
