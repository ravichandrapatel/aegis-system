#!/usr/bin/env python3
# file_name: sync_skills.py
# description: Generate .github/skills/ from .cursor/skills/ so the two never drift.
# version: 1.0.0
# authors: contributors
"""
intent: Make `.cursor/skills/` the single source of truth for agent skills.
role: repo maintenance tool (also runs in CI as a drift gate).

The two trees were previously kept in sync by hand, which guarantees drift.
Run with --check in CI to fail when the generated copies are stale.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".cursor" / "skills"
TARGET = ROOT / ".github" / "skills"

BANNER = (
    "<!-- GENERATED FILE — do not edit.\n"
    "     Source: .cursor/skills/{name}/SKILL.md\n"
    "     Regenerate: python3 tools/sync_skills.py -->\n"
)


def _render(name: str, text: str) -> str:
    """
    intent: Produce the Copilot copy of one Cursor skill.
    input: skill directory name; source markdown.
    output: rendered markdown with a generated-file banner.
    role: pure transform.
    side_effects: none.

    Relative links are identical because both trees sit at the same depth
    (`.cursor/skills/<name>/` and `.github/skills/<name>/`).
    """
    banner = BANNER.format(name=name)
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            cut = end + len("\n---\n")
            return text[:cut] + "\n" + banner + text[cut:].lstrip("\n")
    return banner + "\n" + text


def _pairs() -> list[tuple[str, Path, Path]]:
    out: list[tuple[str, Path, Path]] = []
    for skill_md in sorted(SOURCE.glob("*/SKILL.md")):
        name = skill_md.parent.name
        out.append((name, skill_md, TARGET / name / "SKILL.md"))
    return out


def main(argv: list[str] | None = None) -> int:
    """
    intent: Write (or verify) the generated Copilot skill tree.
    input: --check to verify without writing.
    output: 0 when in sync / written; 1 when --check finds drift.
    role: entry point.
    side_effects: writes under .github/skills/ unless --check.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if copies are stale")
    args = ap.parse_args(argv)

    pairs = _pairs()
    if not pairs:
        print(f"[sync_skills] no skills found under {SOURCE}", file=sys.stderr)
        return 1

    stale: list[str] = []
    for name, src, dst in pairs:
        rendered = _render(name, src.read_text(encoding="utf-8"))
        current = dst.read_text(encoding="utf-8") if dst.is_file() else None
        if current == rendered:
            continue
        if args.check:
            stale.append(name)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rendered, encoding="utf-8")
        print(f"[sync_skills] wrote {dst.relative_to(ROOT)}")

    # Remove generated skills whose source was deleted.
    known = {name for name, _, _ in pairs}
    for existing in sorted(TARGET.glob("*/SKILL.md")):
        if existing.parent.name in known:
            continue
        if args.check:
            stale.append(f"{existing.parent.name} (orphan)")
            continue
        existing.unlink()
        existing.parent.rmdir()
        print(f"[sync_skills] removed orphan {existing.relative_to(ROOT)}")

    if stale:
        print(
            "[sync_skills] out of date: "
            + ", ".join(stale)
            + "\nRun: python3 tools/sync_skills.py",
            file=sys.stderr,
        )
        return 1
    print(f"[sync_skills] {len(pairs)} skill(s) in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
