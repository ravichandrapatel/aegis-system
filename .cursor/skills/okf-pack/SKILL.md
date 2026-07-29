---
name: okf-pack
description: >-
  Build an OKF Prompt Pack (Aegis Rule #1). Use before planning, generation, or
  multi-file edits when the Brain is enabled; or when the user asks to pack/lookup.
---

Build a Prompt Pack. Inject **only** `## Prompt Card` text. Never paste `index.json`, `graph.json`, or full vault bodies.

## How to run

From package root (directory with `AGENTS.md`):

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"
```

Fallback:

```bash
python3 _okf_knowledge/kernel/okf.py lookup --card --limit 3 "<task keywords>"
```

Prefer keywords from the user task (domain + verbs). Cards with matching `pack_force_when` are force-included.

## After pack

1. Use returned cards as binding constraints.
2. If branching decisions remain → `grill-me`.
3. If high-risk → `mutation-gate` before applying.
4. Ladder for missing facts: OKF → card pointers → repo corpus → live upstream → `okf-writeback`.

## Guardrails

- Run `aegis-discover` first on non-trivial turns when env is uncertain.
- **FORBIDDEN:** invent compliance without a pack when Brain is available.
