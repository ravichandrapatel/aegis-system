---
type: Concept
title: OKF Prompt Injection
description: Rule #1 pack/lookup — inject slim Prompt Cards; retrieval ladder OKF → corpus → live → write-back.
tags: [standard, okf, prompting, tokens, aegis, retrieval]
timestamp: 2026-07-28T00:30:00Z
status: active
---

# OKF Prompt Injection

Implements **Rule #1 — Pack first** from [AGENTS.md](/AGENTS.md).

Curated OKF stays in the vault. Generation context gets a **dynamic Prompt Pack**: slim `## Prompt Card` text from this turn’s `okf.py pack` / `lookup --card` — not a full-brain dump.

## Retrieval ladder

| Priority | Lane | How | Use for |
| :---: | :--- | :--- | :--- |
| 1 | OKF | `okf.py pack` / `lookup --card` | Standards, playbooks, catalogs, pins on cards |
| 2 | Card pointers | Read only paths the **current cards** name | One deep dive |
| 3 | Task corpus | Glob → **ripgrep (`rg`)** → Read | Product code in this repository (never legacy `grep`) |
| 4 | Live external | Official Git/OCI/`gh` | Pins still missing/stale after 1–3 |
| 5 | Grader | Only to explain/fix a failure | Not for inventing compliance at author time |

Lane 1 **MUST** run before corpus or authoring. Write-back durable pins/recipes to `_inbox/` (Rung 1); ingest via maintain playbook.

**FORBIDDEN:** paste `graph.json` / full standards into the prompt; skip pack and grep the vault for compliance; invent stub designs that omit wiring the current Prompt Pack requires.

## Budgets

- Each card **SHOULD** be ≤ ~600 characters (~150 tokens).
- Pack for one turn **SHOULD** stay near the budget passed to `pack` (default guidance ~1200 tokens).
- Concepts may set `pack_force_when: [keywords]` so pack force-includes them.

## Prompt Card

```text
Rule #1: okf.py pack (or lookup --card) before authoring; inject ## Prompt Card text only.
Ladder: OKF → card paths → repo corpus → live upstream → write-back _inbox.
No graph/full-doc paste; no grader mining to invent compliance.
```

# Related

- DNA: [AGENTS.md](/AGENTS.md)
- Schema: [OKF House Schema](okf-house-schema.md)
- IDE tokens: [IDE Context Guardrails](ide-context-guardrails.md)
- Pins / caches: [`vault/references/`](/vault/references/) (populate via scrape + maintain)
