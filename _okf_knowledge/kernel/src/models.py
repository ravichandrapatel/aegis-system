"""OKF in-memory models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Concept:
    """
    intent: In-memory representation of one OKF concept document.
    input: populated by load_concept().
    output: n/a (data container).
    role: value object shared by all vault tooling.
    side_effects: none.
    """

    concept_id: str  # path relative to vault root, without .md suffix
    path: Path
    frontmatter: dict[str, object] = field(default_factory=dict)
    body: str = ""
    parse_error: str | None = None


@dataclass
class IndexEntry:
    """
    intent: Slim searchable concept row (frontmatter only).
    input: index.json row or Concept.
    output: n/a.
    role: value object.
    side_effects: none.
    """

    concept_id: str
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    ctype: str = ""
    path: Path | None = None
    # Compile-time normalized fields (filled from index v2; computed on fallback).
    id_norm: str = ""
    title_norm: str = ""
    desc_norm: str = ""
    tags_norm: str = ""
    type_norm: str = ""
    search_tokens: frozenset[str] = field(default_factory=frozenset)
    # Frontmatter pack_force_when: force-include this card when query matches.
    pack_force_when: list[str] = field(default_factory=list)


@dataclass
class Hit:
    """
    intent: One ranked lookup result with debug metadata.
    input: n/a.
    output: n/a.
    role: value object.
    side_effects: none.
    """

    entry: IndexEntry
    score: int
    matched: list[str] = field(default_factory=list)
    graph_hops: int | None = None


@dataclass
class _MtimeCache:
    """Process-local cache invalidated when a file's mtime_ns changes."""

    path: Path | None = None
    mtime_ns: int | None = None
    payload: object | None = None
