#!/usr/bin/env python3
# file_name: okf_lookup.py
# description: Search the Aegis OKF vault by query; return paths and/or Prompt Cards (not full docs).
# version: 0.2.0
# authors: contributors
"""
intent: Cheap vault lookup — compile-time index first, optional Prompt Cards.
input: free-text query; optional --card / --paths / --limit / --type / --max-cards / --budget.
output: ranked hits on stdout; Prompt Cards when --card (budgeted per AGENTS §4.2).
role: CLI for agent routing via vault lookup + Prompt Cards (never fat indexes).
side_effects: none (read-only).

Prefers index.json / prompt_cards.json from graph_compiler; falls back to live vault walk.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from okf_common import BRAIN_ROOT, VAULT_ROOT, Concept, load_vault
from prompt_card import extract_prompt_card

# Tunable field weights (lexical scorer).
TITLE_WEIGHT = 10
ID_WEIGHT = 8
TAG_WEIGHT = 6
DESC_WEIGHT = 3
TYPE_WEIGHT = 2
SLUG_BONUS = 12

# Match-quality multipliers applied to the field weight.
EXACT_MULT = 3
PREFIX_MULT = 2
SUBSTRING_MULT = 1

# Graph proximity bonuses (hops from a strong lexical seed).
GRAPH_HOP1 = 4
GRAPH_HOP2 = 2

MIN_TERM_LEN = 2
DEFAULT_MAX_CARDS = 8
DEFAULT_TOKEN_BUDGET = 1200
# Rough chars≈tokens*4 for budget enforcement without a tokenizer.
CHARS_PER_TOKEN = 4


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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(query: str) -> list[str]:
    return [
        t
        for t in re.split(r"[^a-z0-9_+.-]+", _norm(query))
        if len(t) >= MIN_TERM_LEN
    ]


def _field_score(term: str, hay: str, weight: int) -> tuple[int, str | None]:
    """
    intent: Score one term against one haystack with exact/prefix/substring tiers.
    input: term; normalized haystack; base field weight.
    output: (points, match tier name) or (0, None).
    role: pure scorer helper.
    side_effects: none.
    """
    if not hay or not term:
        return 0, None
    tokens = hay.split()
    if term == hay or term in tokens:
        return weight * EXACT_MULT, "exact"
    if any(tok.startswith(term) for tok in tokens) or hay.startswith(term):
        return weight * PREFIX_MULT, "prefix"
    if term in hay:
        return weight * SUBSTRING_MULT, "substr"
    return 0, None


def score_entry(entry: IndexEntry, terms: list[str]) -> tuple[int, list[str]]:
    """
    intent: Rank an index entry against query terms (frontmatter + id only).
    input: entry; normalized query terms.
    output: (score, matched field names).
    role: pure scorer.
    side_effects: none.
    """
    if not terms:
        return 0, []
    tag_s = " ".join(entry.tags)
    hay = {
        "id": _norm(entry.concept_id.replace("/", " ").replace("-", " ")),
        "title": _norm(entry.title),
        "desc": _norm(entry.description),
        "tags": _norm(tag_s),
        "type": _norm(entry.ctype),
    }
    weights = {
        "id": ID_WEIGHT,
        "title": TITLE_WEIGHT,
        "tags": TAG_WEIGHT,
        "desc": DESC_WEIGHT,
        "type": TYPE_WEIGHT,
    }
    score = 0
    matched: set[str] = set()
    for term in terms:
        for field_name, weight in weights.items():
            pts, tier = _field_score(term, hay[field_name], weight)
            if pts:
                score += pts
                matched.add(field_name if tier == "exact" else f"{field_name}:{tier}")
    slug = "-".join(terms)
    if slug and slug in entry.concept_id.lower():
        score += SLUG_BONUS
        matched.add("slug")
    return score, sorted(matched)


def score_concept(concept: Concept, terms: list[str]) -> int:
    """
    intent: Backward-compatible wrapper over score_entry for Concept objects.
    input: concept; normalized query terms.
    output: integer score (0 = no match).
    role: pure scorer.
    side_effects: none.
    """
    if concept.parse_error:
        return 0
    fm = concept.frontmatter
    tags = fm.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    entry = IndexEntry(
        concept_id=concept.concept_id,
        title=str(fm.get("title", "")),
        description=str(fm.get("description", "")),
        tags=[str(t) for t in tags],
        ctype=str(fm.get("type", "")),
        path=concept.path,
    )
    score, _ = score_entry(entry, terms)
    return score


def _load_index() -> list[IndexEntry] | None:
    """
    intent: Load compile-time index.json when present.
    input: none (reads BRAIN_ROOT/index.json).
    output: entries or None to signal fallback.
    role: index loader.
    side_effects: reads one JSON file.
    """
    path = BRAIN_ROOT / "index.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, list):
        return None
    entries: list[IndexEntry] = []
    for row in raw:
        if not isinstance(row, dict) or "id" not in row:
            continue
        tags = row.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        cid = str(row["id"])
        entries.append(
            IndexEntry(
                concept_id=cid,
                title=str(row.get("title", "")),
                description=str(row.get("description", "")),
                tags=[str(t) for t in tags],
                ctype=str(row.get("type", "")),
                path=VAULT_ROOT / f"{cid}.md",
            )
        )
    return entries


def _entries_from_vault() -> list[IndexEntry]:
    """
    intent: Fallback — build index rows by walking the vault (frontmatter only).
    input: none.
    output: IndexEntry list.
    role: live indexer.
    side_effects: reads vault files.
    """
    entries: list[IndexEntry] = []
    for concept in load_vault():
        if concept.parse_error:
            continue
        fm = concept.frontmatter
        tags = fm.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        entries.append(
            IndexEntry(
                concept_id=concept.concept_id,
                title=str(fm.get("title", "")),
                description=str(fm.get("description", "")),
                tags=[str(t) for t in tags],
                ctype=str(fm.get("type", "")),
                path=concept.path,
            )
        )
    return entries


def _load_adjacency() -> dict[str, set[str]]:
    """
    intent: Undirected adjacency from graph.json for proximity boosts.
    input: none.
    output: concept_id → neighbor ids.
    role: graph loader.
    side_effects: reads graph.json if present.
    """
    path = BRAIN_ROOT / "graph.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    adj: dict[str, set[str]] = {}
    for edge in raw.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src, tgt = edge.get("source"), edge.get("target")
        if not src or not tgt:
            continue
        adj.setdefault(str(src), set()).add(str(tgt))
        adj.setdefault(str(tgt), set()).add(str(src))
    return adj


def _load_card_cache() -> dict[str, str]:
    """
    intent: Load compile-time Prompt Card cache.
    input: none.
    output: concept_id → card body.
    role: card cache loader.
    side_effects: reads prompt_cards.json if present.
    """
    path = BRAIN_ROOT / "prompt_cards.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v}


def _apply_graph_boost(hits: list[Hit], adj: dict[str, set[str]]) -> None:
    """
    intent: Boost hits within 1–2 hops of strong lexical seeds (in-place).
    input: scored hits; adjacency map.
    output: none (mutates hit.score / graph_hops).
    role: ranker.
    side_effects: none.
    """
    if not hits or not adj:
        return
    # Seeds: top lexical scores (at least half of best, min score 20).
    best = max(h.score for h in hits)
    threshold = max(20, best // 2)
    seeds = {h.entry.concept_id for h in hits if h.score >= threshold}
    if not seeds:
        return
    hop1: set[str] = set()
    for s in seeds:
        hop1 |= adj.get(s, set())
    hop1 -= seeds
    hop2: set[str] = set()
    for s in hop1:
        hop2 |= adj.get(s, set())
    hop2 -= seeds | hop1
    by_id = {h.entry.concept_id: h for h in hits}
    for cid in hop1:
        if cid in by_id:
            by_id[cid].score += GRAPH_HOP1
            by_id[cid].graph_hops = 1
    for cid in hop2:
        if cid in by_id:
            by_id[cid].score += GRAPH_HOP2
            by_id[cid].graph_hops = 2


def lookup(
    query: str,
    limit: int = 5,
    type_filter: str | None = None,
) -> list[Hit]:
    """
    intent: Search vault concepts without loading full bodies into ranking.
    input: query; max hits; optional type filter (case-insensitive).
    output: ranked Hit list.
    role: searcher.
    side_effects: reads index.json (or vault) and optionally graph.json.
    """
    terms = _tokens(query)
    entries = _load_index()
    if entries is None:
        entries = _entries_from_vault()
    hits: list[Hit] = []
    want_type = type_filter.lower() if type_filter else None
    for entry in entries:
        if want_type and entry.ctype.lower() != want_type:
            continue
        s, matched = score_entry(entry, terms)
        if s > 0:
            hits.append(Hit(entry=entry, score=s, matched=matched))
    _apply_graph_boost(hits, _load_adjacency())
    hits.sort(key=lambda h: (-h.score, h.entry.concept_id))
    return hits[: max(1, limit)]


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


def _est_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN) if text else 0


def main(argv: list[str] | None = None) -> int:
    """
    intent: CLI — find concepts; optionally emit budgeted Prompt Cards.
    input: argv.
    output: exit 0 if hits; 1 if none / errors.
    role: main.
    side_effects: stdout/stderr only.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Lookup Aegis OKF concepts by query. "
            "Default: list hits. Use --card to print Prompt Cards for agents."
        )
    )
    parser.add_argument("query", help="Search string (title, tags, path, description)")
    parser.add_argument(
        "--card",
        action="store_true",
        help="Emit ## Prompt Card for each hit (skip hits with no card)",
    )
    parser.add_argument(
        "--paths",
        action="store_true",
        help="Print concept paths only (one per line)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max hits (default 5)",
    )
    parser.add_argument(
        "--type",
        dest="type_filter",
        default=None,
        help="Filter by frontmatter type (e.g. Standard, Concept, Playbook)",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=DEFAULT_MAX_CARDS,
        help=f"With --card, stop after N cards (default {DEFAULT_MAX_CARDS})",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=DEFAULT_TOKEN_BUDGET,
        help=(
            f"With --card, approx token budget for the pack "
            f"(default {DEFAULT_TOKEN_BUDGET}; chars//{CHARS_PER_TOKEN})"
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="With --card, include hits that lack a Prompt Card as path stubs",
    )
    args = parser.parse_args(argv)

    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        for hit in hits:
            print(hit.entry.concept_id + ".md")
        return 0

    if args.card:
        cache = _load_card_cache()
        chunks: list[str] = []
        used_tokens = 0
        for hit in hits:
            if len(chunks) >= max(1, args.max_cards):
                break
            card = _card_for(hit, cache)
            if card:
                piece = (
                    f"### Card: {hit.entry.concept_id}.md (score={hit.score})\n{card}"
                )
                cost = _est_tokens(piece)
                if chunks and used_tokens + cost > args.budget:
                    break
                chunks.append(piece)
                used_tokens += cost
            elif args.all:
                stub = (
                    f"### Path: {hit.entry.concept_id}.md (score={hit.score})\n"
                    f"(no ## Prompt Card — open file only if needed)"
                )
                cost = _est_tokens(stub)
                if chunks and used_tokens + cost > args.budget:
                    break
                chunks.append(stub)
                used_tokens += cost
        if not chunks:
            print(
                "[okf_lookup] hits found but none have ## Prompt Card; "
                "re-run without --card or add Prompt Cards",
                file=sys.stderr,
            )
            for hit in hits:
                print(
                    f"  {hit.score:3d}  {hit.entry.concept_id}",
                    file=sys.stderr,
                )
            return 1
        print("\n\n".join(chunks))
        return 0

    # default listing (tiny — safe to show agents as a menu)
    src = "index.json" if (BRAIN_ROOT / "index.json").is_file() else "live vault"
    print(f"# okf_lookup  query={args.query!r}  source={src}  vault={VAULT_ROOT}")
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
            print(f"     ({'; '.join(meta)})")
    print(
        "\n# Next: python3 okf_lookup.py --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
