#!/usr/bin/env python3
# file_name: graph_compiler.py
# description: Compiles vault cross-links into graph.json and embeds them in
#              aegis-brain.html. Stdlib only. (Renamed from toon_compiler.py;
#              context.toon removed — agents use okf_lookup + Prompt Cards.)
# version: 0.3.0
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


def main() -> int:
    """
    intent: Entry point — write graph.json at the vault root and embed the
            graph into aegis-brain.html for file:// auto-load.
    input: none (reads vault from disk).
    output: process exit code.
    role: CLI entry point.
    side_effects: writes graph.json; rewrites aegis-brain.html.
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
        graph_json = json.dumps(graph, indent=2)
        (BRAIN_ROOT / "graph.json").write_text(graph_json + "\n", encoding="utf-8")
        embedded = inject_into_aegis_brain("graph-data", graph_json)
    except OSError as exc:
        print(f"[DBG-201] graph compile failed: {exc}", file=sys.stderr)
        return 1
    skipped_note = f", {len(skipped)} skipped" if skipped else ""
    print(
        f"[DBG-200] wrote graph.json ({len(concepts)} concepts{skipped_note}, "
        f"{len(graph['edges'])} edges) for {VAULT_ROOT}"
        + ("; embedded graph into aegis-brain.html" if embedded else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
