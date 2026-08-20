---
type: Concept
title: IDE Context Guardrails
description: Binding rules to stop IDE token bloat and drift — no @workspace, pack-first cards, rg over legacy search.
tags: [standard, okf, tokens, ide, copilot, cursor, drift]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: ["@workspace", token bloat, context drift, ide context, copilot]
---

# IDE Context Guardrails

Stops **token inflation** and **context drift** in Copilot / Cursor / VS Code when an OKF brain is present. Complements [OKF Prompt Injection](okf-prompt-injection.md) (Rule #1).

## MUST

1. **Explicit scope only** — Name paths, `@file`, or pack/lookup results. **FORBIDDEN:** `@workspace`, “search the whole repo”, or other broad workspace dumps as the primary retrieval move when Brain is enabled.
2. **Pack before corpus** — Non-trivial tasks: `okf.py pack` once (it reports capabilities in the same output); inject **only** `## Prompt Card` text. Do not paste `index.json`, `graph.json`, or full vault/standard bodies. An empty pack ends the retrieval attempt — do not re-query for a hit.
3. **Prefer `rg` (ripgrep)** — `okf.py` lookup cache-miss and IDE file search use **ripgrep only**. **FORBIDDEN:** legacy `grep`/`egrep` as the search backend when `rg` is available.
4. **Preserve grill-me** — Do **not** impose hard chat turn caps that abort challenge-response design reviews. Multi-turn vetting is intentional.

## SHOULD

1. Close unused editor tabs / buffers before long agent sessions so background scanners do not pull idle files into context (e.g. IDE “close all” / `code --close` when that CLI is available).
2. Prefer short, new threads for unrelated tasks over one unbounded chat that re-injects stale tool noise.
3. Keep script/`okf.py` stdout hyper-compressed (JSON pointers / card text) — no conversational wrapper in tool output meant for the model.

## Local cache contract

| Artifact | Role |
| --- | --- |
| `index.json` (v2 + inverted) | Keyword → concept pointers (ms lookup) |
| `prompt_cards.json` | Pre-extracted cards for pack |
| `.okf-compile-cache.json` | Incremental compile cache |

Rebuild with `python3 _okf_knowledge/kernel/okf.py compile`. **JSON** is the on-disk/LLM-facing cache format (native parse weights); do not replace pack payloads with exotic serializations for “token savings.”

## Prompt Card

```text
IDE: no @workspace / broad workspace dump when Brain on — pack cards only.
Pack once per task (it prints caps too); empty pack is final, do not re-query.
Lookup: JSON inverted hit → else ripgrep (rg), never grep; then Prompt Cards.
No hard turn-cap killing grill-me; close idle tabs when possible.
```

# Related

- [OKF Prompt Injection](okf-prompt-injection.md)
- [OKF Cognitive Bundle](/vault/concepts/okf-cognitive-bundle.md)
- DNA: [AGENTS.md](/AGENTS.md)
