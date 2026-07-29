"""Compile graph/index/prompt_cards and incremental cache."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from src.cards import extract_prompt_card
from src.models import Concept
from src.paths import (
    BRAIN_ROOT,
    COMPILE_CACHE_NAME,
    COMPILE_CACHE_VERSION,
    GRAPH_CONTENT_MAX,
    GRAPH_JSON,
    INDEX_FORMAT_VERSION,
    VAULT_ROOT,
)
from src.lookup import (
    _ADJ_CACHE,
    _CARD_CACHE,
    _INDEX_CACHE,
    _INVERTED_CACHE,
    _norm,
    _tokenize,
)
from src.vault import (
    concept_id_from_path,
    extract_links,
    inject_into_aegis_brain,
    iter_concept_files,
    load_vault,
    parse_frontmatter,
    resolve_link,
)


def _graph_content(body: str) -> str:
    stripped = body.strip()
    if len(stripped) <= GRAPH_CONTENT_MAX:
        return stripped
    return stripped[:GRAPH_CONTENT_MAX] + "\n\n…"

def compile_graph(concepts: list[Concept]) -> dict[str, list[dict[str, str]]]:
    """
    intent: Build the node/edge graph implied by markdown cross-links. Nodes
            carry the concept's markdown body so aegis-brain's reading pane
            works without filesystem access.
    input: concepts — loaded vault.
    output: {"nodes": [...], "edges": [...]} dict for graph.json.
    role: graph builder.
    side_effects: none.
    """
    ids = {c.concept_id for c in concepts}
    nodes = [
        {
            "id": c.concept_id,
            "type": str(c.frontmatter.get("type", "?")),
            "title": str(c.frontmatter.get("title", c.path.stem)),
            "description": str(c.frontmatter.get("description", "")),
            "tags": c.frontmatter.get("tags", []),
            "content": _graph_content(c.body),
        }
        for c in concepts
    ]
    edges = []
    for c in concepts:
        for target in extract_links(c.body):
            resolved = resolve_link(target, c.path)
            target_id = concept_id_from_path(resolved)
            if target_id is None:
                continue
            if target_id in ids and target_id != c.concept_id:
                edges.append({"source": c.concept_id, "target": target_id})
    return {"nodes": nodes, "edges": edges}

def _index_row_for_concept(c: Concept) -> dict[str, object]:
    tags = c.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    tag_strs = [str(t) for t in tags]
    title = str(c.frontmatter.get("title", c.path.stem))
    description = str(c.frontmatter.get("description", ""))
    ctype = str(c.frontmatter.get("type", ""))
    id_norm = _norm(c.concept_id.replace("/", " ").replace("-", " "))
    title_norm = _norm(title)
    desc_norm = _norm(description)
    tags_norm = _norm(" ".join(tag_strs))
    type_norm = _norm(ctype)
    tok: set[str] = set()
    tok.update(_tokenize(c.concept_id))
    tok.update(_tokenize(title))
    tok.update(_tokenize(description))
    for t in tag_strs:
        tok.update(_tokenize(t))
    tok.update(_tokenize(ctype))
    pfw = c.frontmatter.get("pack_force_when", [])
    if not isinstance(pfw, list):
        pfw = [pfw] if pfw else []
    pfw_strs = [str(x).strip() for x in pfw if str(x).strip()]
    for kw in pfw_strs:
        tok.update(_tokenize(kw))
    return {
        "id": c.concept_id,
        "path": c.concept_id + ".md",
        "title": title,
        "description": description,
        "tags": tag_strs,
        "type": ctype,
        "id_norm": id_norm,
        "title_norm": title_norm,
        "desc_norm": desc_norm,
        "tags_norm": tags_norm,
        "type_norm": type_norm,
        "tokens": sorted(tok),
        "pack_force_when": pfw_strs,
    }

def compile_index(concepts: list[Concept]) -> dict[str, object]:
    """
    intent: Slim frontmatter index + inverted token map for lookup.
    input: concepts — parseable vault concepts.
    output: index.json v2 document {version, entries, inverted}.
    role: lookup index builder.
    side_effects: none.
    """
    entries = [_index_row_for_concept(c) for c in concepts]
    inverted: dict[str, list[str]] = {}
    for row in entries:
        cid = str(row["id"])
        for tok in row.get("tokens", []):
            inverted.setdefault(str(tok), []).append(cid)
    for key in inverted:
        inverted[key] = sorted(set(inverted[key]))
    return {
        "version": INDEX_FORMAT_VERSION,
        "entries": entries,
        "inverted": inverted,
    }

def compile_prompt_cards(concepts: list[Concept]) -> dict[str, str]:
    """
    intent: Cache ## Prompt Card bodies at compile time so lookup need not
            reopen markdown for winners.
    input: concepts — parseable vault concepts (body available).
    output: concept_id → card body map for prompt_cards.json.
    role: prompt card cache builder.
    side_effects: none.
    """
    cards: dict[str, str] = {}
    for c in concepts:
        card = extract_prompt_card(c.body)
        if card:
            cards[c.concept_id] = card
    return cards

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _compile_cache_path() -> Path:
    return BRAIN_ROOT / COMPILE_CACHE_NAME

def _concept_to_cache(c: Concept) -> dict[str, object]:
    return {
        "concept_id": c.concept_id,
        "frontmatter": c.frontmatter,
        "body": c.body,
        "parse_error": c.parse_error,
    }

def _concept_from_cache(path: Path, blob: dict[str, object]) -> Concept:
    fm = blob.get("frontmatter")
    if not isinstance(fm, dict):
        fm = {}
    return Concept(
        concept_id=str(blob.get("concept_id") or concept_id_from_path(path) or path.stem),
        path=path,
        frontmatter=fm,
        body=str(blob.get("body") or ""),
        parse_error=str(blob["parse_error"]) if blob.get("parse_error") else None,
    )

def load_vault_incremental(force: bool = False) -> tuple[list[Concept], int, int]:
    """
    intent: Load vault concepts, reusing compile-cache entries when mtime/hash match.
    input: force — ignore cache and re-parse everything.
    output: (concepts including parse errors, dirty_count, reused_count).
    role: incremental vault loader.
    side_effects: may rewrite .okf-compile-cache.json.
    """
    cache_path = _compile_cache_path()
    prev: dict[str, object] = {}
    if not force and cache_path.is_file():
        try:
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("version") == COMPILE_CACHE_VERSION:
                prev = loaded
        except (OSError, json.JSONDecodeError):
            prev = {}
    prev_files = prev.get("files") if isinstance(prev.get("files"), dict) else {}

    new_files: dict[str, object] = {}
    concepts: list[Concept] = []
    dirty = 0
    reused = 0

    for path in iter_concept_files():
        rel = str(path.relative_to(VAULT_ROOT)).replace("\\", "/")
        try:
            st = path.stat()
            mtime_ns = st.st_mtime_ns
        except OSError as exc:
            concepts.append(
                Concept(
                    concept_id=concept_id_from_path(path) or path.stem,
                    path=path,
                    parse_error=str(exc),
                )
            )
            dirty += 1
            continue

        cached = prev_files.get(rel) if isinstance(prev_files, dict) else None
        if (
            not force
            and isinstance(cached, dict)
            and cached.get("mtime_ns") == mtime_ns
            and isinstance(cached.get("concept"), dict)
        ):
            concepts.append(_concept_from_cache(path, cached["concept"]))  # type: ignore[arg-type]
            new_files[rel] = cached
            reused += 1
            continue

        try:
            data = path.read_bytes()
        except OSError as exc:
            concepts.append(
                Concept(
                    concept_id=concept_id_from_path(path) or path.stem,
                    path=path,
                    parse_error=str(exc),
                )
            )
            dirty += 1
            continue

        digest = _sha256_bytes(data)
        if (
            not force
            and isinstance(cached, dict)
            and cached.get("sha256") == digest
            and isinstance(cached.get("concept"), dict)
        ):
            cached = dict(cached)
            cached["mtime_ns"] = mtime_ns
            concepts.append(_concept_from_cache(path, cached["concept"]))  # type: ignore[arg-type]
            new_files[rel] = cached
            reused += 1
            continue

        text = data.decode("utf-8")
        fm, body = parse_frontmatter(text)
        cid = concept_id_from_path(path) or path.stem
        if fm is None:
            c = Concept(concept_id=cid, path=path, parse_error="missing/invalid frontmatter")
        else:
            c = Concept(concept_id=cid, path=path, frontmatter=fm, body=body)
        concepts.append(c)
        new_files[rel] = {
            "mtime_ns": mtime_ns,
            "sha256": digest,
            "concept": _concept_to_cache(c),
        }
        dirty += 1

    try:
        cache_path.write_text(
            json.dumps(
                {"version": COMPILE_CACHE_VERSION, "files": new_files},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    # Bust in-process artifact caches after compile inputs change.
    if dirty or force:
        for slot in (_INDEX_CACHE, _ADJ_CACHE, _CARD_CACHE, _INVERTED_CACHE):
            slot.mtime_ns = None
            slot.payload = None

    return concepts, dirty, reused

def _artifacts_fresh(concept_count: int) -> bool:
    """True when index/graph/cards exist and look like a complete prior compile."""
    index_p = BRAIN_ROOT / "index.json"
    cards_p = BRAIN_ROOT / "prompt_cards.json"
    if not (index_p.is_file() and GRAPH_JSON.is_file() and cards_p.is_file()):
        return False
    try:
        raw = json.loads(index_p.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
            return len(raw["entries"]) == concept_count and raw.get("version") == INDEX_FORMAT_VERSION
        if isinstance(raw, list):
            return False  # force upgrade to v2
    except (OSError, json.JSONDecodeError):
        return False
    return False

def cmd_compile(args: object | None = None) -> int:
    """
    intent: Write graph.json, index.json (v2+inverted), prompt_cards.json;
            embed graph into aegis-brain.html. Skips work when the incremental
            compile cache reports zero dirty concepts and artifacts are already
            current (unless --force).
    input: optional --force.
    output: process exit code.
    role: subcommand.
    side_effects: writes graph/index/prompt_cards JSON; updates cache; may rewrite HTML.
    """
    force = bool(getattr(args, "force", False)) if args is not None else False
    try:
        all_concepts, dirty, reused = load_vault_incremental(force=force)
        skipped = [c for c in all_concepts if c.parse_error is not None]
        for c in skipped:
            print(
                f"[DBG-202] skipping unparseable concept {c.concept_id}: {c.parse_error}",
                file=sys.stderr,
            )
        concepts = [c for c in all_concepts if c.parse_error is None]

        if not force and dirty == 0 and _artifacts_fresh(len(concepts)):
            print(
                f"[DBG-200] compile up-to-date ({len(concepts)} concepts, "
                f"{reused} cache hits, 0 dirty) — skipped rewrite for {VAULT_ROOT}"
            )
            return 0

        # Drop legacy TOON index if present from older Aegis versions.
        legacy = BRAIN_ROOT / "context.toon"
        if legacy.exists():
            legacy.unlink()
        graph = compile_graph(concepts)
        index = compile_index(concepts)
        cards = compile_prompt_cards(concepts)
        graph_json = json.dumps(graph, indent=2)
        GRAPH_JSON.write_text(graph_json + "\n", encoding="utf-8")
        (BRAIN_ROOT / "index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
        (BRAIN_ROOT / "prompt_cards.json").write_text(
            json.dumps(cards, indent=2) + "\n", encoding="utf-8"
        )
        # Refresh process caches immediately.
        for slot in (_INDEX_CACHE, _ADJ_CACHE, _CARD_CACHE, _INVERTED_CACHE):
            slot.mtime_ns = None
            slot.payload = None
        embedded = inject_into_aegis_brain("graph-data", graph_json)
    except OSError as exc:
        print(f"[DBG-201] graph compile failed: {exc}", file=sys.stderr)
        return 1
    skipped_note = f", {len(skipped)} skipped" if skipped else ""
    inv_n = len(index.get("inverted", {})) if isinstance(index, dict) else 0
    print(
        f"[DBG-200] wrote graph.json ({len(concepts)} concepts{skipped_note}, "
        f"{len(graph['edges'])} edges), index.json v{INDEX_FORMAT_VERSION} "
        f"({inv_n} inv tokens), prompt_cards.json ({len(cards)} cards); "
        f"parsed={dirty} reused={reused} for {VAULT_ROOT}"
        + ("; embedded graph into aegis-brain.html" if embedded else "")
    )
    return 0

