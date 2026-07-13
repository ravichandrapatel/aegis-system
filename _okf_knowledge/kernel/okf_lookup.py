#!/usr/bin/env python3
# file_name: okf_lookup.py
# description: Search the Aegis OKF vault by query; return paths and/or Prompt Cards (not full docs).
# version: 0.1.0
# authors: contributors
"""
intent: Cheap vault lookup — like okf-generator's `okf lookup`, but for curated Aegis concepts.
input: free-text query; optional --card / --paths / --limit.
output: ranked hits on stdout; Prompt Cards when --card (default for single strong hit).
role: CLI for agent routing via vault lookup + Prompt Cards (never fat indexes).
side_effects: none (read-only).

Unlike UmairBaig8/okf-generator (AST code maps), this indexes vault frontmatter + tags.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

from okf_common import Concept, VAULT_ROOT, load_vault
from prompt_card import extract_prompt_card


@dataclass
class Hit:
    """
    intent: One ranked lookup result.
    input: n/a.
    output: n/a.
    role: value object.
    side_effects: none.
    """

    concept: Concept
    score: int


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9_+.-]+", _norm(query)) if t]


def score_concept(concept: Concept, terms: list[str]) -> int:
    """
    intent: Rank a concept against query terms (frontmatter + id only — cheap).
    input: concept; normalized query terms.
    output: integer score (0 = no match).
    role: pure scorer.
    side_effects: none.
    """
    if concept.parse_error or not terms:
        return 0
    fm = concept.frontmatter
    title = str(fm.get("title", ""))
    desc = str(fm.get("description", ""))
    ctype = str(fm.get("type", ""))
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        tag_s = " ".join(str(t) for t in tags)
    else:
        tag_s = str(tags)
    hay = {
        "id": _norm(concept.concept_id.replace("/", " ").replace("-", " ")),
        "title": _norm(title),
        "desc": _norm(desc),
        "tags": _norm(tag_s),
        "type": _norm(ctype),
    }
    score = 0
    for term in terms:
        if term in hay["id"]:
            score += 8
        if term in hay["title"]:
            score += 10
        if term in hay["tags"]:
            score += 6
        if term in hay["desc"]:
            score += 3
        if term in hay["type"]:
            score += 2
        # phrase-ish: whole query slug in id
    slug = "-".join(terms)
    if slug and slug in concept.concept_id.lower():
        score += 12
    return score


def lookup(query: str, limit: int = 5) -> list[Hit]:
    """
    intent: Search vault concepts without loading full bodies into ranking.
    input: query string; max hits.
    output: ranked Hit list.
    role: searcher.
    side_effects: reads vault files (frontmatter via load_vault).
    """
    terms = _tokens(query)
    hits: list[Hit] = []
    for concept in load_vault():
        s = score_concept(concept, terms)
        if s > 0:
            hits.append(Hit(concept=concept, score=s))
    hits.sort(key=lambda h: (-h.score, h.concept.concept_id))
    return hits[: max(1, limit)]


def main(argv: list[str] | None = None) -> int:
    """
    intent: CLI — find concepts; optionally emit Prompt Cards for injection.
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
        "--all",
        action="store_true",
        help="With --card, include hits that lack a Prompt Card as path stubs",
    )
    args = parser.parse_args(argv)

    hits = lookup(args.query, limit=args.limit)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        for hit in hits:
            print(hit.concept.concept_id + ".md")
        return 0

    if args.card:
        chunks: list[str] = []
        for hit in hits:
            text = hit.concept.path.read_text(encoding="utf-8")
            card = extract_prompt_card(text)
            if card:
                chunks.append(
                    f"### Card: {hit.concept.concept_id}.md (score={hit.score})\n{card}"
                )
            elif args.all:
                chunks.append(
                    f"### Path: {hit.concept.concept_id}.md (score={hit.score})\n"
                    f"(no ## Prompt Card — open file only if needed)"
                )
        if not chunks:
            print(
                "[okf_lookup] hits found but none have ## Prompt Card; "
                "re-run without --card or add Prompt Cards",
                file=sys.stderr,
            )
            for hit in hits:
                print(
                    f"  {hit.score:3d}  {hit.concept.concept_id}",
                    file=sys.stderr,
                )
            return 1
        print("\n\n".join(chunks))
        return 0

    # default listing (tiny — safe to show agents as a menu)
    print(f"# okf_lookup  query={args.query!r}  vault={VAULT_ROOT}")
    for hit in hits:
        fm = hit.concept.frontmatter
        title = fm.get("title", "")
        ctype = fm.get("type", "")
        desc = fm.get("description", "")
        print(f"{hit.score:3d}  [{ctype}]  {hit.concept.concept_id}")
        print(f"     {title} — {desc}")
    print(
        "\n# Next: python3 okf_lookup.py --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
