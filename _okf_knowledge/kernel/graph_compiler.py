#!/usr/bin/env python3
# file_name: graph_compiler.py
# description: Compiles vault cross-links into graph.json, slim index.json /
#              prompt_cards.json for okf_lookup, and embeds graph in
#              aegis-brain.html. Stdlib only. (Renamed from toon_compiler.py;
#              context.toon removed — agents use okf_lookup + Prompt Cards.)
# version: 0.4.0
# authors: contributors
from __future__ import annotations

import json
import sys

from okf_common import (
    BRAIN_ROOT,
    GRAPH_CONTENT_MAX,
    VAULT_ROOT,
    Concept,
    concept_id_from_path,
    extract_links,
    inject_into_aegis_brain,
    load_vault,
    resolve_link,
)
from prompt_card import extract_prompt_card


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


def compile_index(concepts: list[Concept]) -> list[dict[str, object]]:
    """
    intent: Slim frontmatter index for okf_lookup (no bodies — cheap retrieval).
    input: concepts — parseable vault concepts.
    output: list of index entries for index.json.
    role: lookup index builder.
    side_effects: none.
    """
    entries: list[dict[str, object]] = []
    for c in concepts:
        tags = c.frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        entries.append(
            {
                "id": c.concept_id,
                "path": c.concept_id + ".md",
                "title": str(c.frontmatter.get("title", c.path.stem)),
                "description": str(c.frontmatter.get("description", "")),
                "tags": [str(t) for t in tags],
                "type": str(c.frontmatter.get("type", "")),
            }
        )
    return entries


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


def main() -> int:
    """
    intent: Entry point — write graph.json, index.json, prompt_cards.json and
            embed the graph into aegis-brain.html for file:// auto-load.
    input: none (reads vault from disk).
    output: process exit code.
    role: CLI entry point.
    side_effects: writes graph/index/prompt_cards JSON; rewrites aegis-brain.html.
    """
    try:
        all_concepts = load_vault()
        skipped = [c for c in all_concepts if c.parse_error is not None]
        for c in skipped:
            print(
                f"[DBG-202] skipping unparseable concept {c.concept_id}: {c.parse_error}",
                file=sys.stderr,
            )
        concepts = [c for c in all_concepts if c.parse_error is None]
        # Drop legacy TOON index if present from older Aegis versions.
        legacy = BRAIN_ROOT / "context.toon"
        if legacy.exists():
            legacy.unlink()
        graph = compile_graph(concepts)
        index = compile_index(concepts)
        cards = compile_prompt_cards(concepts)
        graph_json = json.dumps(graph, indent=2)
        (BRAIN_ROOT / "graph.json").write_text(graph_json + "\n", encoding="utf-8")
        (BRAIN_ROOT / "index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
        (BRAIN_ROOT / "prompt_cards.json").write_text(
            json.dumps(cards, indent=2) + "\n", encoding="utf-8"
        )
        embedded = inject_into_aegis_brain("graph-data", graph_json)
    except OSError as exc:
        print(f"[DBG-201] graph compile failed: {exc}", file=sys.stderr)
        return 1
    skipped_note = f", {len(skipped)} skipped" if skipped else ""
    print(
        f"[DBG-200] wrote graph.json ({len(concepts)} concepts{skipped_note}, "
        f"{len(graph['edges'])} edges), index.json, prompt_cards.json "
        f"({len(cards)} cards) for {VAULT_ROOT}"
        + ("; embedded graph into aegis-brain.html" if embedded else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
