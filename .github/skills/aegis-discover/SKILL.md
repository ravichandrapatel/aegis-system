---
name: aegis-discover
description: >-
  Run Aegis Capability Discovery before non-trivial work. Use when starting a
  task, after environment change, or when unsure whether Brain/Git/Python exist.
---

Probe what exists. Enable only reported features. Policy (disable table, hard rules): [`AGENTS.md`](../../../AGENTS.md) § Capability Discovery · packable: [`aegis-capability-discovery.md`](../../../_okf_knowledge/vault/concepts/aegis-capability-discovery.md).

## How to run

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Emit a short Capability Report: cap statuses + `enabled_features` + `runtime_hint`.

## Guardrails

- Brain missing on non-trivial CREATE/MODIFY → `BLOCKED` (do not freestyle).
- If `okf.py` missing: shell-probe only — **never** claim a successful Prompt Pack.
- Trivial Q&A may skip. Next: `okf-pack` when Brain is present.
