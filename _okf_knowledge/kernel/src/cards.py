"""Prompt Card extraction and card CLI."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from src.paths import PROMPT_CARD_MAX_CHARS, VAULT_ROOT


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

_CARD_TITLE = re.compile(r"^prompt\s+card$", re.I)

def extract_prompt_card(text: str) -> str | None:
    """
    intent: Return the body under the first ## Prompt Card heading.
    input: full markdown text.
    output: card body string (stripped) or None if missing/empty.
    role: pure extractor.
    side_effects: none.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _HEADING_RE.match(lines[i])
        if m and _CARD_TITLE.match(m.group(2).strip()):
            level = len(m.group(1))
            i += 1
            body: list[str] = []
            while i < len(lines):
                m2 = _HEADING_RE.match(lines[i])
                if m2 and len(m2.group(1)) <= level:
                    break
                body.append(lines[i])
                i += 1
            card = "\n".join(body).strip()
            return card or None
        i += 1
    return None

def _resolve_card_path(raw: str) -> Path:
    """
    intent: Resolve a user path against CWD or vault root.
    input: raw path string.
    output: absolute Path.
    role: pure resolver.
    side_effects: none.
    """
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    candidate = (VAULT_ROOT / raw).resolve()
    if candidate.is_file():
        return candidate
    # allow paths relative to package root (parent of vault)
    pkg = VAULT_ROOT.parent / raw
    if pkg.is_file():
        return pkg.resolve()
    return p.resolve()

def cmd_card(args: argparse.Namespace) -> int:
    """
    intent: Emit Prompt Cards for known paths or fail if any missing.
    input: parsed args (paths, --max-chars).
    output: exit 0 on success, 1 on missing card/file.
    role: subcommand.
    side_effects: reads files; prints to stdout/stderr.
    """
    chunks: list[str] = []
    errors = 0
    for raw in args.paths:
        path = _resolve_card_path(raw)
        if not path.is_file():
            print(f"[prompt_card] missing file: {raw}", file=sys.stderr)
            errors += 1
            continue
        text = path.read_text(encoding="utf-8")
        card = extract_prompt_card(text)
        if card is None:
            print(f"[prompt_card] no ## Prompt Card in {path}", file=sys.stderr)
            errors += 1
            continue
        if len(card) > args.max_chars:
            print(
                f"[prompt_card] WARN {path.name}: {len(card)} chars > {args.max_chars}",
                file=sys.stderr,
            )
        rel = path
        try:
            rel = path.relative_to(VAULT_ROOT)
        except ValueError:
            pass
        chunks.append(f"### Card: {rel}\n{card}")

    if errors:
        return 1
    print("\n\n".join(chunks))
    return 0

