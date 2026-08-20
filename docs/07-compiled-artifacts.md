# 7. Compiled artifacts

[← Table of contents](README.md)

These build outputs from the kernel tools make retrieval and visualization cheap. They are **not** meant to be pasted into LLM generation prompts.

Regenerate after brain edits:

```bash
python3 _okf_knowledge/kernel/okf.py compile   # index + prompt_cards + HTML graph embed
python3 _okf_knowledge/kernel/okf.py lint      # console report + HTML lint embed
```

> **On-disk artifacts:** `index.json` (v2 + inverted), `prompt_cards.json` at the
> brain root, and `kernel/okf/assets/graph.json` (nodes/edges for hop-boost, card
> `related:` edges, and serve). Graph and lint
> payloads are **also embedded** inside `okf-brain.html` by `compile` / `lint`.
> There is **no** `lint.json` sidecar. `.okf-compile-cache.json` is gitignored.

## At-a-glance comparison

| Artifact | Produced by | Primary consumer | Contains | Paste into LLM? |
| --- | --- | --- | --- | --- |
| **`index.json`** | `okf.py compile` | `okf.py lookup` | Slim frontmatter rows + inverted token map (v2) | **MUST NOT** |
| **`prompt_cards.json`** | `okf.py compile` | `okf.py pack` / `lookup --card` | Cached `## Prompt Card` bodies | Emit **selected** cards only (budgeted) |
| **`kernel/okf/assets/graph.json`** | `okf.py compile` | lookup hop-boost, pack `related:` edges, serve `/graph.json` | Nodes, edges, truncated bodies | **MUST NOT** |
| **Graph embed** (in `okf-brain.html`) | `okf.py compile` | Brain UI | Same graph payload embedded | **MUST NOT** |
| **Lint embed** (in `okf-brain.html`) | `okf.py lint` | Brain UI / CI summary | Lint findings | No (fixational) |
| **`okf-brain.html`** | hand-maintained shell + embed updates | Humans in browser | Visualizer + embedded graph/lint payloads | n/a |

## `index.json` — slim lookup index

### Purpose

Make vault search **O(read one JSON)** instead of **O(open every markdown + parse YAML)** on each query. Format **v2** carries the **inverted token map** (candidate narrowing). Graph hop-boost adjacency is loaded from `kernel/okf/assets/graph.json`, not from `index.json`.

### Shape (conceptual)

```json
{
  "version": 2,
  "entries": [
    {
      "id": "standards/okf-prompt-injection",
      "path": "standards/okf-prompt-injection.md",
      "title": "OKF Prompt Injection",
      "description": "…",
      "tags": ["standard", "okf", "prompting"],
      "type": "Concept",
      "resource": "",
      "trust": "unverified",
      "stale_after": ""
    }
  ],
  "inverted": { "token": ["concept-id", "…"] }
}
```

`resource` is carried through from frontmatter so `pack` can print the card's `source:` line without reopening the markdown. It is **not** tokenized or scored — see [Frontmatter schema](05-frontmatter-schema.md#resource-pointer-to-the-described-thing).

`trust` is the tier **derived** from `verified` at compile time (static content); `stale_after` is carried raw, because staleness depends on when the pack is built, not when it was compiled. Both feed the card's `trust:` line — see [Lookup — Trust labels](08-lookup-and-prompt-cards.md#trust-labels-on-cards).

### When to use

- Always prefer this path via `okf.py lookup` (automatic if the file exists).
- Debugging ranking: inspect which fields/tokens are present for a concept.

### When **not** to use

- Do not hand-edit; regenerate with `okf.py compile`.
- Do not treat as agent context dump.

### Fallback

If `index.json` is missing, lookup walks the live vault (slower). After any ingest, recompile so the index stays fresh.

## `prompt_cards.json` — Prompt Card cache

### Purpose

Avoid re-parsing markdown bodies when emitting `--card` results for winning hits.

### Shape (conceptual)

```json
{
  "standards/simplicity-first": "Laziness Ladder: reuse → one-file edit → …",
  "standards/okf-prompt-injection": "Rule #1: okf.py pack (or lookup --card) before authoring …"
}
```

### When to use

- Indirectly: `okf.py lookup --card` loads this cache first, then falls back to reading `.md` on miss.

### When **not** to use

- Do not paste the **entire** JSON into a prompt.
- Do not edit by hand — change the source `## Prompt Card` section, then recompile.

## Graph embed — system graph (inside `okf-brain.html`)

### Purpose

- Power the **okf-brain** visualizer (nodes/edges reading pane).
- Support **dependency discovery** during Context Expansion — lookup hop-boost reads adjacency from `kernel/okf/assets/graph.json`.
- Feed **traversal**: `pack` reads the same adjacency to print each card's `related:` line, so the agent can walk to a neighbour instead of re-querying.

### Shape (conceptual)

```json
{
  "nodes": [
    { "id": "standards/simplicity-first", "type": "Concept", "title": "…",
      "description": "…", "tags": ["…"], "content": "…truncated body…" }
  ],
  "edges": [ { "source": "…", "target": "…" } ]
}
```

Edges come from markdown cross-links between concepts. They are **untyped**: every edge is exactly `{source, target}`, both ends being concept ids that exist in the vault. Self-links and links that leave the vault are skipped.

### When to use

| Use | How |
| --- | --- |
| Explore relationships visually | `okf.py serve` → `okf-brain.html` |
| Walk dependencies for Prompt Pack assembly | Traverse edges; then load **Prompt Cards**, not node `content` |
| Boost lookup ranking by proximity | Lookup reads `graph.json` adjacency for hop bonuses |
| Traverse on from a pack | `pack` prints up to 3 neighbours per card as `related:` — open one of those paths |

### When **not** to use

- As the generation prompt itself.
- As a substitute for `index.json` search (too heavy; includes bodies).

### Edge semantics

The compiler does **not** emit typed edges. Relationship vocabulary (`depends_on`, `implements`, `compatible_with`, …) is an agent reasoning convention documented in [Protocol](06-protocol-routing.md#graph-edges-convention--kernel-edges-are-untyped) — it is expressed in document prose, not in `graph.json`, and no code reads it.

## Lint embed (inside `okf-brain.html`)

Machine-readable lint report for the visualizer, refreshed by `okf.py lint`. Treat **exit code / console summary** as the operator signal; the embed is for tooling/UI.

## Mental model: compile once, query many

```
Vault markdown (source of truth)
        │
        ▼
 okf.py compile
        │
        ├──► index.json          (search fields + inverted tokens)
        ├──► prompt_cards.json   (injection snippets)
        ├──► kernel/okf/assets/graph.json (nodes/edges; hop-boost, related:, serve)
        └──► okf-brain.html    (graph embed; lint embed via okf.py lint)

lookup:   index.json → score (+ graph.json hop-boost) → prompt_cards.json (winners only)
pack:     …the same, then graph.json adjacency → related: footer under each card
```

## Related

- [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md)
- [Kernel tools](09-kernel-tools.md)
