"""Reference normalize / optimize."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from src.cards import extract_prompt_card
from src.compile_cmd import cmd_compile
from src.paths import VAULT_ROOT
from src.vault import escape_yaml_scalar, format_frontmatter, load_concept, parse_frontmatter


VAULT_DIR = VAULT_ROOT / "vault"

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

def _reference_cache_dirs() -> list[Path]:
    """
    intent: Discover directories under vault/ that hold Reference concepts.
    input: none (walks VAULT_DIR).
    output: sorted unique parent dirs of files with frontmatter type Reference.
    role: dynamic replacement for a static allowlist — new scrape/cache dirs
          (e.g. vault/github-actions/, vault/terraform/) are picked up automatically.
    side_effects: none (read-only).
    """
    if not VAULT_DIR.is_dir():
        return []
    dirs: set[Path] = set()
    for path in VAULT_DIR.rglob("*.md"):
        if path.name == "index.md":
            continue
        if any(part.startswith(".") for part in path.relative_to(VAULT_DIR).parts):
            continue
        if _is_reference(path):
            dirs.add(path.parent)
    return sorted(dirs)

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
    intent: Regenerate indexes for every directory that contains References.
    input: none (discovers dirs via _reference_cache_dirs()).
    output: number of index files written.
    role: index generator scoped by frontmatter type, not by hardcoded dir names.
    side_effects: writes index.md under discovered Reference dirs only.
    """
    written = 0
    for source_dir in _reference_cache_dirs():
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
            rel = source_dir.relative_to(VAULT_DIR)
            body = f"# Cached references — {rel}\n\n" + "\n".join(entries) + "\n"
            (source_dir / "index.md").write_text(body, encoding="utf-8")
            written += 1
    return written

def cmd_optimize(_args: argparse.Namespace | None = None) -> int:
    """
    intent: Normalize References only, rebuild their indexes, recompile.
    input: none.
    output: process exit code.
    role: subcommand.
    side_effects: rewrites Reference files + their indexes; runs compile.
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
    return cmd_compile()

