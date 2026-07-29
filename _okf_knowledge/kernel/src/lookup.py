"""Lookup, scoring, Prompt Pack assembly, lookup/pack CLIs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from src.cards import extract_prompt_card
from src.config import count_tokens, load_okf_config
from src.models import Hit, IndexEntry, _MtimeCache
from src.paths import (
    BRAIN_ROOT,
    DEFAULT_MAX_CARDS,
    DEFAULT_TOKEN_BUDGET,
    DESC_WEIGHT,
    EXACT_MULT,
    GRAPH_HOP1,
    GRAPH_HOP2,
    GRAPH_JSON,
    ID_WEIGHT,
    MIN_TERM_LEN,
    PREFIX_MULT,
    SLUG_BONUS,
    SUBSTRING_MULT,
    TAG_WEIGHT,
    TITLE_WEIGHT,
    TYPE_WEIGHT,
    VAULT_ROOT,
    _CAMEL_RE,
)
from src.vault import load_vault


_INDEX_CACHE = _MtimeCache()

_ADJ_CACHE = _MtimeCache()

_CARD_CACHE = _MtimeCache()

_INVERTED_CACHE = _MtimeCache()

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

def _tokenize(text: str) -> list[str]:
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

def _tokens(query: str) -> list[str]:
    # Preserve order, drop dupes.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in _tokenize(query):
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered

def _ensure_norms(entry: IndexEntry) -> None:
    """Fill normalized fields / search tokens when missing (v1 index or vault)."""
    if entry.id_norm and entry.search_tokens:
        return
    id_raw = entry.concept_id.replace("/", " ").replace("-", " ")
    entry.id_norm = entry.id_norm or _norm(id_raw)
    entry.title_norm = entry.title_norm or _norm(entry.title)
    entry.desc_norm = entry.desc_norm or _norm(entry.description)
    entry.tags_norm = entry.tags_norm or _norm(" ".join(entry.tags))
    entry.type_norm = entry.type_norm or _norm(entry.ctype)
    if not entry.search_tokens:
        bag = set(_tokenize(entry.concept_id))
        bag.update(_tokenize(entry.title))
        bag.update(_tokenize(entry.description))
        for t in entry.tags:
            bag.update(_tokenize(str(t)))
        bag.update(_tokenize(entry.ctype))
        entry.search_tokens = frozenset(bag)

def _field_score(term: str, hay: str, weight: int, hay_tokens: set[str] | None = None) -> tuple[int, str | None]:
    """
    intent: Score one term against one haystack with exact/prefix/substring tiers.
    input: term; normalized haystack; base field weight; optional token set.
    output: (points, match tier name) or (0, None).
    role: pure scorer helper.
    side_effects: none.
    """
    if not hay or not term:
        return 0, None
    tokens = hay_tokens if hay_tokens is not None else set(hay.split())
    if term == hay or term in tokens:
        return weight * EXACT_MULT, "exact"
    if any(tok.startswith(term) for tok in tokens) or hay.startswith(term):
        return weight * PREFIX_MULT, "prefix"
    if term in hay:
        return weight * SUBSTRING_MULT, "substr"
    # Acronym: term chars match successive word initials (e.g. "gha" → github actions)
    if len(term) >= 2:
        ordered = [t for t in hay.split() if t]
        if len(ordered) >= len(term):
            initials = "".join(t[0] for t in ordered)
            if initials.startswith(term):
                return weight * PREFIX_MULT, "acronym"
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
    _ensure_norms(entry)
    hay = {
        "id": entry.id_norm,
        "title": entry.title_norm,
        "desc": entry.desc_norm,
        "tags": entry.tags_norm,
        "type": entry.type_norm,
    }
    hay_tok = {
        "id": set(entry.id_norm.split()),
        "title": set(entry.title_norm.split()),
        "desc": set(entry.desc_norm.split()),
        "tags": set(entry.tags_norm.split()),
        "type": set(entry.type_norm.split()),
    }
    # Merge camelCase search tokens into title/id bags for subword hits.
    hay_tok["title"] |= set(entry.search_tokens)
    hay_tok["id"] |= set(entry.search_tokens)
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
        # Direct token hit from compile-time bag (cheap camelCase/snake match).
        if term in entry.search_tokens:
            score += TITLE_WEIGHT * PREFIX_MULT
            matched.add("token")
        for field_name, weight in weights.items():
            pts, tier = _field_score(term, hay[field_name], weight, hay_tok[field_name])
            if pts:
                score += pts
                matched.add(field_name if tier == "exact" else f"{field_name}:{tier}")
    slug = "-".join(terms)
    if slug and slug in entry.concept_id.lower():
        score += SLUG_BONUS
        matched.add("slug")
    return score, sorted(matched)

def _read_json_mtime(path: Path) -> tuple[object | None, int | None]:
    if not path.is_file():
        return None, None
    try:
        mtime_ns = path.stat().st_mtime_ns
        return json.loads(path.read_text(encoding="utf-8")), mtime_ns
    except (OSError, json.JSONDecodeError):
        return None, None

def _cached_load(cache: _MtimeCache, path: Path) -> object | None:
    """Return cached payload when path mtime matches; else reload from disk."""
    if not path.is_file():
        cache.path = path
        cache.mtime_ns = None
        cache.payload = None
        return None
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return None
    if cache.path == path and cache.mtime_ns == mtime_ns and cache.payload is not None:
        return cache.payload
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache.path = path
        cache.mtime_ns = None
        cache.payload = None
        return None
    cache.path = path
    cache.mtime_ns = mtime_ns
    cache.payload = raw
    return raw

def _entry_from_row(row: dict) -> IndexEntry | None:
    if "id" not in row:
        return None
    tags = row.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    cid = str(row["id"])
    tok_list = row.get("tokens") or []
    if not isinstance(tok_list, list):
        tok_list = []
    pfw = row.get("pack_force_when", [])
    if not isinstance(pfw, list):
        pfw = [pfw] if pfw else []
    entry = IndexEntry(
        concept_id=cid,
        title=str(row.get("title", "")),
        description=str(row.get("description", "")),
        tags=[str(t) for t in tags],
        ctype=str(row.get("type", "")),
        path=VAULT_ROOT / f"{cid}.md",
        id_norm=str(row.get("id_norm", "")),
        title_norm=str(row.get("title_norm", "")),
        desc_norm=str(row.get("desc_norm", "")),
        tags_norm=str(row.get("tags_norm", "")),
        type_norm=str(row.get("type_norm", "")),
        search_tokens=frozenset(str(t) for t in tok_list if t),
        pack_force_when=[str(x) for x in pfw if str(x).strip()],
    )
    _ensure_norms(entry)
    return entry

def _load_index_bundle() -> tuple[list[IndexEntry] | None, dict[str, list[str]]]:
    """
    intent: Load index.json (+ inverted map) with process-local mtime cache.
    output: (entries or None, inverted token→ids).
    """
    path = BRAIN_ROOT / "index.json"
    raw = _cached_load(_INDEX_CACHE, path)
    if raw is None:
        return None, {}
    inverted: dict[str, list[str]] = {}
    rows: list
    if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
        rows = raw["entries"]
        inv = raw.get("inverted") or {}
        if isinstance(inv, dict):
            inverted = {str(k): [str(x) for x in v] for k, v in inv.items() if isinstance(v, list)}
        # Also keep inverted in its own mtime cache slot (same file).
        _INVERTED_CACHE.path = path
        _INVERTED_CACHE.mtime_ns = _INDEX_CACHE.mtime_ns
        _INVERTED_CACHE.payload = inverted
    elif isinstance(raw, list):
        rows = raw
    else:
        return None, {}
    entries: list[IndexEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry = _entry_from_row(row)
        if entry:
            entries.append(entry)
    return entries, inverted

def _load_index() -> list[IndexEntry] | None:
    """
    intent: Load compile-time index.json when present.
    input: none (reads BRAIN_ROOT/index.json).
    output: entries or None to signal fallback.
    role: index loader.
    side_effects: reads one JSON file (mtime-cached).
    """
    entries, _ = _load_index_bundle()
    return entries

def _load_inverted() -> dict[str, list[str]]:
    _, inv = _load_index_bundle()
    return inv

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
        pfw = fm.get("pack_force_when", [])
        if not isinstance(pfw, list):
            pfw = [pfw] if pfw else []
        entry = IndexEntry(
            concept_id=concept.concept_id,
            title=str(fm.get("title", "")),
            description=str(fm.get("description", "")),
            tags=[str(t) for t in tags],
            ctype=str(fm.get("type", "")),
            path=concept.path,
            pack_force_when=[str(x) for x in pfw if str(x).strip()],
        )
        _ensure_norms(entry)
        entries.append(entry)
    return entries

def _load_adjacency() -> dict[str, set[str]]:
    """
    intent: Undirected adjacency from graph.json for proximity boosts.
    input: none.
    output: concept_id → neighbor ids.
    role: graph loader.
    side_effects: reads graph.json if present (mtime-cached).
    """
    path = GRAPH_JSON
    raw = _cached_load(_ADJ_CACHE, path)
    if not isinstance(raw, dict):
        return {}
    # Cache parsed adjacency, not raw JSON, on second access path:
    cached_adj = getattr(_ADJ_CACHE, "_adj", None)
    if (
        cached_adj is not None
        and _ADJ_CACHE.path == path
        and getattr(_ADJ_CACHE, "_adj_mtime", None) == _ADJ_CACHE.mtime_ns
    ):
        return cached_adj  # type: ignore[return-value]
    adj: dict[str, set[str]] = {}
    for edge in raw.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src, tgt = edge.get("source"), edge.get("target")
        if not src or not tgt:
            continue
        adj.setdefault(str(src), set()).add(str(tgt))
        adj.setdefault(str(tgt), set()).add(str(src))
    _ADJ_CACHE._adj = adj  # type: ignore[attr-defined]
    _ADJ_CACHE._adj_mtime = _ADJ_CACHE.mtime_ns  # type: ignore[attr-defined]
    return adj

def _load_card_cache() -> dict[str, str]:
    """
    intent: Load compile-time Prompt Card cache.
    input: none.
    output: concept_id → card body.
    role: card cache loader.
    side_effects: reads prompt_cards.json if present (mtime-cached).
    """
    path = BRAIN_ROOT / "prompt_cards.json"
    raw = _cached_load(_CARD_CACHE, path)
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

def _candidate_ids(terms: list[str], inverted: dict[str, list[str]], all_ids: list[str]) -> list[str] | None:
    """
    intent: Narrow scoring set via inverted index (union of term postings).
    output: candidate ids, or None to score everyone (no inv / empty terms /
            any term with no posting — keeps acronym/fuzzy recall).
    """
    if not terms or not inverted:
        return None
    found: set[str] = set()
    for t in terms:
        hit_this = False
        ids = inverted.get(t)
        if ids:
            found.update(ids)
            hit_this = True
        # Prefix expansion for short typed queries (e.g. "work" → workflow)
        if len(t) >= 3:
            for key, postings in inverted.items():
                if key.startswith(t):
                    found.update(postings)
                    hit_this = True
        if not hit_this:
            return None  # unknown token → full scan (acronym / fuzzy)
    if not found:
        return None
    allow = found
    return [cid for cid in all_ids if cid in allow]

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
    entries, inverted = _load_index_bundle()
    if entries is None:
        entries = _entries_from_vault()
        inverted = {}
    by_id = {e.concept_id: e for e in entries}
    candidate_ids = _candidate_ids(terms, inverted, list(by_id.keys()))
    if candidate_ids is None:
        pool = entries
    else:
        pool = [by_id[cid] for cid in candidate_ids if cid in by_id]
    hits: list[Hit] = []
    want_type = type_filter.lower() if type_filter else None
    for entry in pool:
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
    """Backward-compatible alias for count_tokens."""
    return count_tokens(text)

def _query_matches_pack_force(query: str, keywords: list[str]) -> bool:
    """True when any pack_force_when keyword appears as a phrase in the query."""
    if not keywords:
        return False
    q = (query or "").lower()
    for kw in keywords:
        k = kw.lower().strip()
        if k and k in q:
            return True
    return False

def _force_hits_for_query(query: str, type_filter: str | None = None) -> list[Hit]:
    """
    intent: Force-include index entries whose pack_force_when matches the query.
    AGENTS.md: pack/lookup force-includes matching concepts over live rediscovery.
    """
    entries = _load_index()
    if entries is None:
        entries = _entries_from_vault()
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
                score=10_000,
                matched=["pack_force_when"],
                graph_hops=None,
            )
        )
    return forced

def assemble_prompt_pack(
    query: str,
    *,
    limit: int = 5,
    type_filter: str | None = None,
    max_cards: int | None = None,
    budget: int | None = None,
) -> tuple[list[dict[str, object]], list]:
    """
    intent: Shared Prompt Pack builder for lookup --card and pack.
    output: (pack rows, raw hits). Each row: id, score, kind, text, tokens.
    Force-includes concepts with matching pack_force_when before ranked hits.
    """
    cfg = load_okf_config()
    max_cards = int(max_cards if max_cards is not None else cfg.get("max_cards", DEFAULT_MAX_CARDS))
    budget = int(budget if budget is not None else cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))
    ranked = lookup(query, limit=limit, type_filter=type_filter)
    forced = _force_hits_for_query(query, type_filter=type_filter)
    # Force-include first, then ranked (dedupe by concept_id).
    merged: list[Hit] = []
    seen_ids: set[str] = set()
    for hit in forced + list(ranked or []):
        cid = hit.entry.concept_id
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        merged.append(hit)
    hits = merged
    if not hits:
        return [], []
    cache = _load_card_cache()
    pack: list[dict[str, object]] = []
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
        if pack and used + cost > budget:
            break
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
        used += cost
    return pack, hits

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
            "<okf_prompt_pack>",
            f"  <query>{_xml_esc(query)}</query>",
            f"  <total_tokens>{total}</total_tokens>",
        ]
        for r in pack:
            lines.append(
                f'  <card id="{_xml_esc(str(r["id"]))}" tokens="{r["tokens"]}" '
                f'score="{r["score"]}" kind="{r["kind"]}">'
            )
            lines.append(f"    <![CDATA[{r['text']}]]>")
            lines.append("  </card>")
        lines.append("</okf_prompt_pack>")
        return "\n".join(lines)
    header = (
        f"# OKF Prompt Pack\nquery: {query!r}\n"
        f"cards: {len(pack)}  total_tokens: {total}\n"
    )
    body = "\n\n".join(str(r["text"]) for r in pack)
    return header + "\n" + body if pack else header + "\n(no cards)\n"

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
        )
        if not hits:
            print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
            return 1
        if as_json:
            print(format_pack(pack, "json", args.query))
        else:
            # agent-facing: cards only (no pack header) — same as pre-1.2
            print("\n\n".join(str(r["text"]) for r in pack))
        return 0

    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
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
        _, inv = _load_index_bundle()
        src = f"index.json v{INDEX_FORMAT_VERSION}"
        if inv:
            src += f" (inv={len(inv)} tokens)"
    else:
        src = "live vault"
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
    intent: Export a cards-only Prompt Pack (Repomix-like formats, OKF semantics).
    """
    pack, hits = assemble_prompt_pack(
        args.query,
        limit=args.limit,
        type_filter=args.type_filter,
        max_cards=args.max_cards,
        budget=args.budget,
    )
    if not hits:
        print(f"[okf_pack] no hits for: {args.query!r}", file=sys.stderr)
        return 1
    out = format_pack(pack, args.style, args.query)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"[okf_pack] wrote {args.output} ({len(pack)} cards)", file=sys.stderr)
    else:
        print(out)
    return 0

