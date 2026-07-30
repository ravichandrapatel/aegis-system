---
applyTo: "**"
---

# Aegis OKF (BINDING) — Copilot path instructions

Same binding as [`.github/copilot-instructions.md`](../copilot-instructions.md). DNA: root [`AGENTS.md`](../../AGENTS.md).

When editing workflows, actions, or OKF docs:

1. `python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"` before inventing policy or layout.
2. Follow house standards on returned Prompt Cards (not assumed domain packs).
3. After durable OKF changes: `compile` then `lint` (0 errors).
4. Explicit `@file` / paths — not `@workspace` — when Brain is on ([ide-context-guardrails](../../_okf_knowledge/standards/ide-context-guardrails.md)).
