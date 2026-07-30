# 8. Compiled artifacts

[← Table of contents](README.md)

These build outputs from the kernel tools make retrieval and visualization cheap. They are **not** meant to be pasted into LLM generation prompts.

Regenerate after brain edits:

```bash
python3 _okf_knowledge/kernel/okf.py compile   # index + prompt_cards + HTML graph embed
python3 _okf_knowledge/kernel/okf.py lint      # console report + HTML lint embed
```

> **On-disk artifacts:** `index.json` (v2 + inverted), `prompt_cards.json`, and
> `kernel/src/graph.json` (nodes/edges for hop-boost + serve). Graph and lint
> payloads are **also embedded** inside `aegis-brain.html` by `compile` / `lint`.
> There is **no** `lint.json` sidecar. `.okf-compile-cache.json` is gitignored.

## At-a-glance comparison

| Artifact | Produced by | Primary consumer | Contains | Paste into LLM? |
| --- | --- | --- | --- | --- |
| **`index.json`** | `okf.py compile` | `okf.py lookup` | Slim frontmatter rows + inverted token map (v2) | **MUST NOT** |
| **`prompt_cards.json`** | `okf.py compile` | `okf.py lookup --card` | Cached `## Prompt Card` bodies | Emit **selected** cards only (budgeted) |
| **`kernel/src/graph.json`** | `okf.py compile` | lookup hop-boost + serve `/graph.json` | Nodes, edges, truncated bodies | **MUST NOT** |
| **Graph embed** (in `aegis-brain.html`) | `okf.py compile` | Brain UI | Same graph payload embedded | **MUST NOT** |
| **Lint embed** (in `aegis-brain.html`) | `okf.py lint` | Brain UI / CI summary | Lint findings | No (fixational) |
| **`aegis-brain.html`** | hand-maintained shell + embed updates | Humans in browser | Visualizer + embedded graph/lint payloads | n/a |

## `index.json` — slim lookup index

### Purpose

Make vault search **O(read one JSON)** instead of **O(open every markdown + parse YAML)** on each query. Format **v2** carries the **inverted token map** (candidate narrowing). Graph hop-boost adjacency is loaded from `kernel/src/graph.json`, not from `index.json`.

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
      "type": "Concept"
    }
  ],
  "inverted": { "token": ["concept-id", "…"] }
}
```

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
  "standards/simplicity-first": "Rule #1 Laziness Ladder: …",
  "standards/okf-prompt-injection": "OKF inject MUST: …"
}
```

### When to use

- Indirectly: `okf.py lookup --card` loads this cache first, then falls back to reading `.md` on miss.

### When **not** to use

- Do not paste the **entire** JSON into a prompt.
- Do not edit by hand — change the source `## Prompt Card` section, then recompile.

## Graph embed — system graph (inside `aegis-brain.html`)

### Purpose

- Power the **aegis-brain** visualizer (nodes/edges reading pane).
- Support **dependency discovery** during Context Expansion — lookup hop-boost reads adjacency from `kernel/src/graph.json`.

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

Edges come from markdown cross-links between concepts.

### When to use

| Use | How |
| --- | --- |
| Explore relationships visually | `okf.py serve` → `aegis-brain.html` |
| Walk dependencies for Prompt Pack assembly | Traverse edges; then load **Prompt Cards**, not node `content` |
| Boost lookup ranking by proximity | Lookup reads `index.json` adjacency for hop bonuses |

### When **not** to use

- As the generation prompt itself.
- As a substitute for `index.json` search (too heavy; includes bodies).

### Protocol edge semantics

Agents must respect typed edges such as `depends_on`, `implements`, `governed_by`, `references`, `compatible_with`, `supersedes` (see [Protocol](06-protocol-routing.md)). The compiler’s link-derived edges are the baseline graph; richer typing can be layered as the vault grows.

## Lint embed (inside `aegis-brain.html`)

Machine-readable lint report for the visualizer, refreshed by `okf.py lint`. Treat **exit code / console summary** as the operator signal; the embed is for tooling/UI.

## Mental model: compile once, query many

```
Vault markdown (source of truth)
        │
        ▼
 okf.py compile
        │
        ├──► index.json          (search fields + inverted + adjacency)
        ├──► prompt_cards.json   (injection snippets)
        └──► aegis-brain.html    (graph embed; lint embed via okf.py lint)

lookup:   index.json → score (+ adjacency hop-boost) → prompt_cards.json (winners only)
```

## Related

- [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md)
- [Kernel tools](10-kernel-tools.md)
