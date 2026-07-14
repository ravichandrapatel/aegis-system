# 8. Compiled artifacts

[← Table of contents](README.md)

These JSON (and HTML) files are **build outputs** from kernel tools. They make retrieval and visualization cheap. They are **not** meant to be pasted into LLM generation prompts.

Regenerate after brain edits:

```bash
python3 _okf_knowledge/kernel/okf.py compile   # graph + index + prompt_cards (+ HTML embed)
python3 _okf_knowledge/kernel/okf.py lint         # lint.json
```

## At-a-glance comparison

| File | Produced by | Primary consumer | Contains | Paste into LLM? |
| --- | --- | --- | --- | --- |
| **`graph.json`** | `okf.py compile` | Brain UI; typed traversal tooling | Nodes, edges, truncated bodies | **MUST NOT** |
| **`index.json`** | `okf.py compile` | `okf.py lookup` | Slim frontmatter rows only | **MUST NOT** |
| **`prompt_cards.json`** | `okf.py compile` | `okf.py lookup --card` | Cached `## Prompt Card` bodies | Emit **selected** cards only (budgeted) |
| **`lint.json`** | `okf.py lint` | Brain UI / CI summary | Lint findings | No (fixational) |
| **`aegis-brain.html`** | hand-maintained + embed updates | Humans in browser | Visualizer shell + embedded graph | n/a |

## `graph.json` — system graph

### Purpose

- Power the **aegis-brain** visualizer (nodes/edges reading pane).
- Support **dependency discovery** during Context Expansion (`AGENTS.md` §1.4 / §4.2).

### Shape (conceptual)

```json
{
  "nodes": [
    {
      "id": "standards/simplicity-first",
      "type": "Concept",
      "title": "…",
      "description": "…",
      "tags": ["…"],
      "content": "…truncated body…"
    }
  ],
  "edges": [
    { "source": "…", "target": "…" }
  ]
}
```

### When to use

| Use | How |
| --- | --- |
| Explore relationships visually | Open via `okf.py serve` → `aegis-brain.html` |
| Walk dependencies for Prompt Pack assembly | Traverse edges; then load **Prompt Cards**, not node `content` |
| Boost lookup ranking by proximity | `okf_lookup` may read adjacency for hop bonuses |

### When **not** to use

- As the generation prompt itself.
- As a substitute for `index.json` search (too heavy; includes bodies).

### Protocol edge semantics

Agents must respect typed edges such as `depends_on`, `implements`, `governed_by`, `references`, `compatible_with`, `supersedes` (see [Protocol](06-protocol-routing.md)). The compiler’s link-derived edges are the baseline graph; richer typing can be layered as the vault grows.

## `index.json` — slim lookup index

### Purpose

Make vault search **O(read one JSON)** instead of **O(open every markdown + parse YAML)** on each query.

### Shape (conceptual)

```json
[
  {
    "id": "standards/okf-prompt-injection",
    "path": "standards/okf-prompt-injection.md",
    "title": "OKF Prompt Injection",
    "description": "…",
    "tags": ["standard", "okf", "prompting"],
    "type": "Concept"
  }
]
```

### When to use

- Always prefer this path via `okf.py lookup` (automatic if the file exists).
- Debugging ranking: inspect which fields are present for a concept.

### When **not** to use

- Do not hand-edit; regenerate with `okf.py compile`.
- Do not treat as agent context dump.

### Fallback

If `index.json` is missing, `okf_lookup` walks the live vault (slower). After any ingest, recompile so the index stays fresh.

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

## `lint.json`

Machine-readable lint report for the visualizer and CI summaries. Produced by `okf.py lint`. Treat **exit code / console summary** as the operator signal; JSON is for tooling.

## Mental model: compile once, query many

```
Vault markdown (source of truth)
        │
        ▼
 okf.py compile
        │
        ├──► graph.json          (structure + UI bodies)
        ├──► index.json          (search fields)
        └──► prompt_cards.json   (injection snippets)

okf_lookup:  index.json → score → prompt_cards.json (winners only)
traversal:   graph.json edges → choose candidates → cards
```

## Related

- [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md)
- [Kernel tools](10-kernel-tools.md)
- [ADR D5 — graph is not agent context](../ADR.md)
