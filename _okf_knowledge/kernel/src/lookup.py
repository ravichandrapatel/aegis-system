"""Lookup, scoring, inverted index, and ripgrep fallback."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from src.models import Hit, IndexEntry, _MtimeCache
from src.paths import (
    BRAIN_ROOT,
    DESC_WEIGHT,
    EXACT_MULT,
    GRAPH_HOP1,
    GRAPH_HOP2,
    GRAPH_JSON,
    ID_WEIGHT,
    PREFIX_MULT,
    RESERVED_FILENAMES,
    SLUG_BONUS,
    SUBSTRING_MULT,
    TAG_WEIGHT,
    TITLE_WEIGHT,
    TYPE_WEIGHT,
    VAULT_ROOT,
)
from src.vault import concept_id_from_path, load_vault
from src.textutil import norm as _norm, tokenize as _tokenize

# Soft cap for rg file hits before scoring (keeps pack budgets small).
_RG_MAX_FILES = 40
_RG_TIMEOUT_S = 8


_INDEX_CACHE = _MtimeCache()
_ADJ_CACHE = _MtimeCache()
_CARD_CACHE = _MtimeCache()
_INVERTED_CACHE = _MtimeCache()

# Public aliases for compile cache busting / pack_cmd (stable API).
INDEX_CACHE = _INDEX_CACHE
ADJ_CACHE = _ADJ_CACHE
CARD_CACHE = _CARD_CACHE
INVERTED_CACHE = _INVERTED_CACHE

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

def _entry_from_concept(concept) -> IndexEntry | None:
    if concept.parse_error:
        return None
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
    return entry

def _entries_from_vault() -> list[IndexEntry]:
    """
    intent: Last-resort fallback — walk vault frontmatter (no grep; prefer rg first).
    input: none.
    output: IndexEntry list.
    role: live indexer.
    side_effects: reads vault files.
    """
    entries: list[IndexEntry] = []
    for concept in load_vault():
        entry = _entry_from_concept(concept)
        if entry:
            entries.append(entry)
    return entries

def _rg_bin() -> str | None:
    """
    intent: Resolve ripgrep binary; never use legacy grep.
    output: path to rg or None.
    """
    return shutil.which("rg")

def _rg_concept_ids(query: str, *, max_files: int = _RG_MAX_FILES) -> list[str]:
    """
    intent: Cache-miss body search via ripgrep only (no grep/egrep).
    input: query string; max file hits.
    output: ordered unique concept_ids under BRAIN_ROOT.
    role: rg fallback searcher.
    side_effects: may spawn `rg` subprocess (no shell).
    """
    rg = _rg_bin()
    if not rg:
        return []
    terms = [t for t in _tokens(query) if len(t) >= 3]
    raw = (query or "").strip()
    patterns: list[str] = []
    if raw and len(raw) >= 3:
        patterns.append(re.escape(raw))
    for t in terms[:6]:
        esc = re.escape(t)
        if esc not in patterns:
            patterns.append(esc)
    if not patterns:
        return []
    # Prefer fewer false positives: OR of substantial terms / full phrase.
    pattern = "|".join(patterns)
    cmd = [
        rg,
        "-l",
        "-i",
        "--glob",
        "*.md",
        "--glob",
        "!**/kernel/src/**",
        "--glob",
        "!**/.okf-compile-cache.json",
        "-e",
        pattern,
        str(BRAIN_ROOT),
    ]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=_RG_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode not in (0, 1):
        # 0 = matches, 1 = no matches; other = error
        return []
    ids: list[str] = []
    seen: set[str] = set()
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        cid = concept_id_from_path(Path(line))
        if not cid:
            continue
        base = cid.rsplit("/", 1)[-1] + ".md"
        if base in RESERVED_FILENAMES or cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)
        if len(ids) >= max(1, max_files):
            break
    return ids

def _entries_for_ids(
    concept_ids: list[str],
    by_id: dict[str, IndexEntry] | None = None,
) -> list[IndexEntry]:
    """
    intent: Resolve IndexEntry rows for concept ids (index first, else vault parse).
    """
    out: list[IndexEntry] = []
    have = by_id or {}
    need_vault: list[str] = []
    for cid in concept_ids:
        if cid in have:
            out.append(have[cid])
        else:
            need_vault.append(cid)
    if not need_vault:
        return out
    wanted = set(need_vault)
    for concept in load_vault():
        if concept.concept_id not in wanted:
            continue
        entry = _entry_from_concept(concept)
        if entry:
            out.append(entry)
            wanted.discard(entry.concept_id)
        if not wanted:
            break
    return out

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
    intent: Search vault concepts — JSON inverted index first, ripgrep on miss.
    input: query; max hits; optional type filter (case-insensitive).
    output: ranked Hit list.
    role: searcher.
    side_effects: reads index.json; may spawn `rg` (never grep); may read vault.
    """
    terms = _tokens(query)
    # Prefer substantial tokens for ranking (avoids "me"/"to" noise); keep all if none.
    rank_terms = [t for t in terms if len(t) >= 3] or terms
    entries, inverted = _load_index_bundle()
    source = "index"
    if entries is None:
        # No compiled index → ripgrep discover paths (not grep), else vault walk.
        rg_ids = _rg_concept_ids(query)
        if rg_ids:
            entries = _entries_for_ids(rg_ids)
            source = "rg"
        else:
            entries = _entries_from_vault()
            source = "live-vault"
        inverted = {}
    by_id = {e.concept_id: e for e in entries}
    candidate_ids = _candidate_ids(rank_terms, inverted, list(by_id.keys()))
    if candidate_ids is None:
        pool = entries  # full index / vault scan (fuzzy + acronym recall)
    else:
        pool = [by_id[cid] for cid in candidate_ids if cid in by_id]

    hits: list[Hit] = []
    want_type = type_filter.lower() if type_filter else None
    for entry in pool:
        if want_type and entry.ctype.lower() != want_type:
            continue
        s, matched = score_entry(entry, rank_terms)
        if s > 0:
            if source == "rg" and "rg" not in matched:
                matched = list(matched) + ["rg"]
            hits.append(Hit(entry=entry, score=s, matched=matched))

    # Cache / lexical miss → ripgrep body fallback (never grep).
    if not hits:
        rg_ids = _rg_concept_ids(query)
        if rg_ids:
            for entry in _entries_for_ids(rg_ids, by_id):
                if want_type and entry.ctype.lower() != want_type:
                    continue
                s, matched = score_entry(entry, rank_terms)
                if s <= 0:
                    s = max(1, TITLE_WEIGHT)
                    matched = ["rg"]
                elif "rg" not in matched:
                    matched = list(matched) + ["rg"]
                hits.append(Hit(entry=entry, score=s, matched=matched))
            source = "rg" if source in {"live-vault", "rg"} else "index+rg"

    _apply_graph_boost(hits, _load_adjacency())
    hits.sort(key=lambda h: (-h.score, h.entry.concept_id))
    lookup._last_source = source  # type: ignore[attr-defined]
    return hits[: max(1, limit)]


# Stable public API for pack_cmd / external callers.
load_index_bundle = _load_index_bundle
load_index = _load_index
entries_from_vault = _entries_from_vault
load_card_cache = _load_card_cache
