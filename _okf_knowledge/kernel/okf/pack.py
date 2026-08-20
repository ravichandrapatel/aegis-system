"""Prompt Pack assembly and lookup/pack CLIs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from okf.capabilities import compact_capability_line
from okf.cards import extract_prompt_card
from okf.config import _tiktoken_encoder, count_tokens, load_config
from okf.lookup import (
    entries_from_vault,
    load_adjacency,
    load_card_cache,
    load_index,
    load_index_bundle,
    lookup,
)
from okf.models import Hit
from okf.paths import (
    BRAIN_ROOT,
    DEFAULT_MAX_CARDS,
    DEFAULT_RELATED_LINKS,
    DEFAULT_TOKEN_BUDGET,
    FORCE_SCORE,
    INDEX_FORMAT_VERSION,
    MIN_PACK_SCORE,
    VAULT_ROOT,
)
from okf.textutil import tokenize as _tokenize
from okf.trust import MACHINE_CONFIRMED, is_stale

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

def _query_matches_pack_force(query: str, keywords: list[str]) -> bool:
    """
    intent: True when a pack_force_when keyword appears in the query on token
            boundaries. Multi-word keywords must match as a contiguous phrase.
    input: raw query; keyword list from frontmatter.
    output: bool.
    role: pure matcher.
    side_effects: none.

    Substring matching was wrong: keyword "tab" fired on "table"/"stable",
    "deploy" fired on "deployment", "token" fired on "tokenizer" — each forcing
    an unrelated card in at FORCE_SCORE.
    """
    if not keywords:
        return False
    q_tokens = _tokenize(query or "")
    if not q_tokens:
        return False
    q_set = set(q_tokens)
    for kw in keywords:
        kw_tokens = _tokenize(kw or "")
        if not kw_tokens:
            continue
        if len(kw_tokens) == 1:
            if kw_tokens[0] in q_set:
                return True
            continue
        span = len(kw_tokens)
        for i in range(len(q_tokens) - span + 1):
            if q_tokens[i : i + span] == kw_tokens:
                return True
    return False

def _force_hits_for_query(query: str, type_filter: str | None = None) -> list[Hit]:
    """
    intent: Force-include index entries whose pack_force_when matches the query.
    AGENTS.md: pack/lookup force-includes matching concepts over live rediscovery.
    """
    entries = load_index()
    if entries is None:
        entries = entries_from_vault()
    forced: list[Hit] = []
    seen: set[str] = set()
    for entry in entries:
        if type_filter and entry.ctype.lower() != type_filter.lower():
            continue
        if not _query_matches_pack_force(query, entry.pack_force_when):
            continue
        if entry.concept_id in seen:
            continue
        seen.add(entry.concept_id)
        forced.append(
            Hit(
                entry=entry,
                score=FORCE_SCORE,
                matched=["pack_force_when"],
                graph_hops=None,
            )
        )
    return forced

def _traversal_footer(
    hit: Hit,
    adj: dict[str, set[str]],
    in_pack: set[str],
    limit: int,
) -> str:
    """
    intent: Expose this concept's outbound graph edges so the agent can traverse
            the bundle deliberately (OKF's premise) instead of treating the pack
            as a flat ranked blob, plus the trust signals that qualify how
            far the card should be trusted.
    input: hit; undirected adjacency; ids already selected for the pack; max links.
    output: footer lines ("" when nothing worth adding).
    role: card decorator.
    side_effects: none.

    Neighbours already in the pack are omitted: pointing at a card the agent
    is already holding costs tokens and buys no reach. Trust lines are rare on
    purpose: unverified is the silent default (labeling it on every card was a
    pure token tax while nothing was reviewed), human-reviewed stays silent,
    and only machine-confirmed or stale content pays for a caution line.
    """
    lines: list[str] = []
    caution: list[str] = []
    # Unverified = silent default (no per-card tax). Human-reviewed = silent.
    # Only machine-confirmed (and staleness below) pays for a caution line.
    if hit.entry.trust == MACHINE_CONFIRMED:
        caution.append(MACHINE_CONFIRMED)
    if is_stale({"stale_after": hit.entry.stale_after}):
        caution.append(f"stale since {hit.entry.stale_after}")
    if caution:
        lines.append("trust: " + ", ".join(caution))
    resource = (hit.entry.resource or "").strip()
    if resource:
        lines.append(f"source: {resource}")
    if limit > 0:
        neighbours = sorted(adj.get(hit.entry.concept_id, set()) - in_pack)
        if neighbours:
            shown = " · ".join(f"{cid}.md" for cid in neighbours[:limit])
            more = len(neighbours) - limit
            suffix = f" (+{more} more)" if more > 0 else ""
            lines.append(f"related: {shown}{suffix}")
    return ("\n" + "\n".join(lines)) if lines else ""


def _truncate_to_budget(body: str, budget: int) -> str:
    """
    intent: Clamp a single oversized card to the token budget.
    input: card text; token budget.
    output: text costing <= budget tokens, with a truncation marker.
    role: budget guard.
    side_effects: none.
    """
    if budget <= 0 or count_tokens(body) <= budget:
        return body
    marker = "\n… (card truncated to fit token budget)"
    lines = body.splitlines()
    kept: list[str] = []
    for line in lines:
        candidate = "\n".join(kept + [line]) + marker
        if count_tokens(candidate) > budget:
            break
        kept.append(line)
    return ("\n".join(kept) + marker) if kept else marker.strip()


def assemble_prompt_pack(
    query: str,
    *,
    limit: int = 5,
    type_filter: str | None = None,
    max_cards: int | None = None,
    budget: int | None = None,
    min_score: int | None = None,
    related_links: int | None = None,
) -> tuple[list[dict[str, object]], list]:
    """
    intent: Shared Prompt Pack builder for lookup --card and pack.
    output: (pack rows, raw hits). Each row: id, score, kind, text, tokens.
    Force-includes concepts with matching pack_force_when before ranked hits,
    then drops ranked hits below min_score so an off-topic query returns an
    empty pack instead of a confident irrelevant card. Selected cards carry
    their graph edges so the agent can traverse on from the pack.
    """
    cfg = load_config()
    max_cards = int(max_cards if max_cards is not None else cfg.get("max_cards", DEFAULT_MAX_CARDS))
    budget = int(budget if budget is not None else cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))
    floor = int(min_score if min_score is not None else cfg.get("min_pack_score", MIN_PACK_SCORE))
    rel_n = int(
        related_links
        if related_links is not None
        else cfg.get("related_links", DEFAULT_RELATED_LINKS)
    )
    ranked = lookup(query, limit=limit, type_filter=type_filter)
    forced = _force_hits_for_query(query, type_filter=type_filter)
    # Force-include first, then ranked above the relevance floor (dedupe by id).
    merged: list[Hit] = []
    seen_ids: set[str] = set()
    for hit in forced + list(ranked or []):
        cid = hit.entry.concept_id
        if cid in seen_ids:
            continue
        if hit.score < floor:
            continue
        seen_ids.add(cid)
        merged.append(hit)
    hits = merged
    if not hits:
        return [], []
    cache = load_card_cache()
    pack: list[dict[str, object]] = []
    chosen: list[Hit] = []
    used = 0
    for hit in hits:
        if len(pack) >= max(1, max_cards):
            break
        card = _card_for(hit, cache)
        if card:
            kind = "card"
            body = f"### Card: {hit.entry.concept_id}.md (score={hit.score})\n{card}"
        else:
            kind = "stub"
            body = (
                f"### Path: _okf_knowledge/{hit.entry.concept_id}.md "
                f"(score={hit.score})\n"
                f"(no ## Prompt Card — open file only if needed)"
            )
        cost = count_tokens(body)
        if used + cost > budget:
            # Always emit at least one card, but never silently blow the budget:
            # an oversized first card is truncated to the budget instead.
            if pack:
                break
            body = _truncate_to_budget(body, budget)
            cost = count_tokens(body)
        pack.append(
            {
                "id": hit.entry.concept_id,
                "path": hit.entry.concept_id + ".md",
                "type": hit.entry.ctype,
                "title": hit.entry.title,
                "score": hit.score,
                "kind": kind,
                "text": body,
                "tokens": cost,
            }
        )
        chosen.append(hit)
        used += cost
    _attach_traversal(pack, chosen, budget=budget, used=used, limit=rel_n)
    return pack, hits


def _attach_traversal(
    pack: list[dict[str, object]],
    chosen: list[Hit],
    *,
    budget: int,
    used: int,
    limit: int,
) -> None:
    """
    intent: Append graph edges (and any `resource`) to selected cards in place,
            after selection so footers never displace a card.
    input: pack rows; the hits behind them; token budget and spend so far.
    output: none (mutates pack rows).
    role: budget-aware decorator.
    side_effects: reads graph.json via the adjacency cache.
    """
    if not pack:
        return
    adj = load_adjacency() if limit > 0 else {}
    in_pack = {str(row["id"]) for row in pack}
    for row, hit in zip(pack, chosen):
        footer = _traversal_footer(hit, adj, in_pack, limit)
        if not footer:
            continue
        cost = count_tokens(footer)
        if used + cost > budget:
            break
        row["text"] = str(row["text"]) + footer
        row["tokens"] = int(row["tokens"]) + cost
        used += cost

def _cdata(text: str) -> str:
    """
    intent: Embed text in XML CDATA without breakout on ]]> sequences.
    input: raw text (may contain ]]> ).
    output: CDATA markup safe for XML parsers.
    """
    # Standard split: "]]>" → "]]]]><![CDATA[>" so no section contains terminator.
    safe = str(text).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe}]]>"


def format_pack(pack: list[dict[str, object]], style: str, query: str) -> str:
    """Render Prompt Pack as markdown | json | xml (cards only — never full vault)."""
    total = sum(int(r["tokens"]) for r in pack)
    style = (style or "markdown").lower()
    if style == "json":
        return json.dumps(
            {
                "query": query,
                "token_estimator": "tiktoken:cl100k_base" if _tiktoken_encoder() else "heuristic",
                "total_tokens": total,
                "cards": [
                    {
                        "id": r["id"],
                        "path": r["path"],
                        "type": r["type"],
                        "title": r["title"],
                        "score": r["score"],
                        "kind": r["kind"],
                        "tokens": r["tokens"],
                        "text": r["text"],
                    }
                    for r in pack
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    if style == "xml":
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<prompt_pack>",
            f"  <query>{_xml_esc(query)}</query>",
            f"  <total_tokens>{total}</total_tokens>",
        ]
        for r in pack:
            lines.append(
                f'  <card id="{_xml_esc(str(r["id"]))}" tokens="{r["tokens"]}" '
                f'score="{r["score"]}" kind="{_xml_esc(str(r["kind"]))}">'
            )
            lines.append(f"    {_cdata(str(r['text']))}")
            lines.append("  </card>")
        lines.append("</prompt_pack>")
        return "\n".join(lines)
    header = (
        f"# OKF Prompt Pack\nquery: {query!r}\n"
        f"cards: {len(pack)}  total_tokens: {total}\n"
    )
    if not pack:
        return (
            header
            + "\nno relevant cards — the vault has nothing binding on this topic.\n"
            + "Proceed on general engineering judgement; capture anything durable "
            + "to _okf_knowledge/_inbox/.\n"
            + "To browse rather than search, enter at _okf_knowledge/index.md and "
            + "follow its links.\n"
        )
    return header + "\n" + "\n\n".join(str(r["text"]) for r in pack)

def _xml_esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def cmd_lookup(args: argparse.Namespace) -> int:
    """
    intent: Find concepts; optionally emit budgeted Prompt Cards.
    input: parsed args.
    output: exit 0 if hits; 1 if none / errors.
    role: subcommand.
    side_effects: stdout/stderr only.
    """
    as_json = bool(getattr(args, "json", False))

    if args.card:
        pack, hits = assemble_prompt_pack(
            args.query,
            limit=args.limit,
            type_filter=args.type_filter,
            max_cards=args.max_cards,
            budget=args.budget,
            min_score=getattr(args, "min_score", None),
        )
        if not hits:
            print(f"[lookup] no relevant cards for: {args.query!r}", file=sys.stderr)
            return 1
        if as_json:
            print(format_pack(pack, "json", args.query))
        else:
            # agent-facing: cards only (no pack header) — same as pre-1.2
            print("\n\n".join(str(r["text"]) for r in pack))
        return 0

    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        if as_json:
            print(json.dumps([h.entry.concept_id + ".md" for h in hits], indent=2))
        else:
            for hit in hits:
                print(hit.entry.concept_id + ".md")
        return 0

    if as_json:
        print(
            json.dumps(
                [
                    {
                        "id": h.entry.concept_id,
                        "path": h.entry.concept_id + ".md",
                        "type": h.entry.ctype,
                        "title": h.entry.title,
                        "description": h.entry.description,
                        "score": h.score,
                        "matched": h.matched,
                        "graph_hops": h.graph_hops,
                    }
                    for h in hits
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if (BRAIN_ROOT / "index.json").is_file():
        _, inv = load_index_bundle()
        src = getattr(lookup, "_last_source", None) or f"index.json v{INDEX_FORMAT_VERSION}"
        if inv and str(src).startswith("index"):
            src = f"{src} (inv={len(inv)} tokens)"
    else:
        src = getattr(lookup, "_last_source", None) or "rg|live-vault"
    print(f"# okf lookup  query={args.query!r}  source={src}  vault={VAULT_ROOT}")
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
            print(f"     ({' '.join(meta)})")
    print(
        "\n# Next: python3 okf.py lookup --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
    return 0

def cmd_pack(args: argparse.Namespace) -> int:
    """
    intent: Export a cards-only Prompt Pack (Repomix-like formats, OKF semantics)
            with an inline capability line, so Rule #1 and Capability Discovery
            cost one command instead of two.
    input: parsed args.
    output: exit 0 always — an empty pack is a valid answer ("vault knows
            nothing relevant"), not an error, so agents stop retrying.
    role: subcommand.
    side_effects: stdout, or writes --output.
    """
    caps_line = "" if getattr(args, "no_caps", False) else compact_capability_line()
    pack, _hits = assemble_prompt_pack(
        args.query,
        limit=args.limit,
        type_filter=args.type_filter,
        max_cards=args.max_cards,
        budget=args.budget,
        min_score=getattr(args, "min_score", None),
    )
    out = format_pack(pack, args.style, args.query)
    if caps_line and args.style == "markdown":
        out = f"{caps_line}\n{out}"
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"[pack] wrote {args.output} ({len(pack)} cards)", file=sys.stderr)
    else:
        print(out)
    return 0

