---
applyTo: "**"
---

# Aegis OKF (BINDING) — Copilot path instructions

Same binding as [`.github/copilot-instructions.md`](../copilot-instructions.md). DNA: root [`AGENTS.md`](../../AGENTS.md).

When editing GHA YAML, actions, workflows, or OKF docs:

1. `python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"` from package root before inventing policy or layout.
2. Follow house standards surfaced on Prompt Cards (SPVS, layout, commits, pins).
3. After durable OKF changes: `python3 _okf_knowledge/kernel/okf.py compile && python3 _okf_knowledge/kernel/okf.py lint` (0 errors).
