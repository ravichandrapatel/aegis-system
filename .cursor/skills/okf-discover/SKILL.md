---
name: okf-discover
description: >-
  Inspect OKF capabilities in detail. Use only when `pack` reports something
  degraded or BLOCKED, or when the Brain/Python/Git situation is unclear.
---

**Most tasks do not need this skill.** `okf.py pack` already prints a `caps:` line, so running discovery separately costs an extra round trip for information you already have. Reach for this only when that line shows `BLOCKED` or a non-`present` capability and you need the detail.

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

`--strict` exits `4` when `runtime_hint` is `BLOCKED`. Probes: `python`, `filesystem`, `shell`, `brain`, `git`, `compile`, `lint`.

Policy and the full disable table: [`AGENTS.md`](../../../AGENTS.md) § Capability fallback · packable concept: [`okf-capability-discovery.md`](../../../_okf_knowledge/vault/concepts/okf-capability-discovery.md).

## Guardrails

- Enable only the features actually reported. Never assume a tool exists.
- Brain missing on a non-trivial create/modify → `BLOCKED`. Do not freestyle.
- If `okf.py` itself is missing, shell-probe by hand and **never** claim a successful Prompt Pack.
