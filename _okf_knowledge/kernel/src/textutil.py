"""Shared text normalization / tokenization for index + compile."""
from __future__ import annotations

import re

from src.paths import MIN_TERM_LEN, _CAMEL_RE


def norm(text: str) -> str:
    """Collapse whitespace and lowercase."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    """
    intent: Split on whitespace, snake_case, camelCase, and punctuation.
    input: raw text (title, id, query, …).
    output: lowercase tokens (length ≥ MIN_TERM_LEN).
    """
    out: list[str] = []
    for word in re.split(r"[^A-Za-z0-9_+.-]+", text or ""):
        if not word:
            continue
        for part in word.replace("-", "_").split("_"):
            if not part:
                continue
            chunks = _CAMEL_RE.findall(part) or [part]
            for c in chunks:
                t = c.lower()
                if len(t) >= MIN_TERM_LEN:
                    out.append(t)
    return out
