---
name: okf-pack
description: >-
  Build an OKF Prompt Pack (Aegis Rule #1). Use before planning, generation, or
  multi-file edits when the Brain is enabled; or when the user asks to pack/lookup.
---

Inject **only** `## Prompt Card` text. Ladder + budgets: [`okf-prompt-injection.md`](../../../_okf_knowledge/standards/okf-prompt-injection.md). DNA one-liner: [`AGENTS.md`](../../../AGENTS.md) § Rule #1.

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"
# fallback:
python3 _okf_knowledge/kernel/okf.py lookup --card --limit 3 "<task keywords>"
```

## After pack

Cards bind → `grill-me` if branching → `mutation-gate` if high-risk → write-back gaps via `okf-writeback`.

## Guardrails

- Prefer `aegis-discover` first when env is uncertain.
- **FORBIDDEN:** invent compliance without a pack when Brain is available; paste `index.json` / full vault bodies.
