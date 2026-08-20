---
type: Concept
title: OKF Capability Discovery
description: Probe Brain/FS/Python/Git/Shell before enabling pack/compile/lint; folded into pack as a one-line caps header.
tags: [okf-system, capability, discovery, portable]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: [capability discovery, okf.py capabilities, runtime hint]
---

# OKF Capability Discovery

Binding policy (disable table, fallbacks, hard `BLOCKED` rule): **[`AGENTS.md`](/AGENTS.md)** § Capability fallback. Skill recipe: `okf-discover`.

## Normally you get this for free

`okf.py pack` prints a capability line before the cards, so Rule #1 and discovery are one command and one round trip:

```
caps: READY | all present | features: prompt_pack,vault_lookup,compile,lint,rung2_maintain,git_ops
```

Run the standalone command only when that line reports something other than `all present`, or when `okf.py` itself may be missing:

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Probes `python`, `filesystem`, `shell`, `brain`, `git`, `compile`, `lint`. `--strict` exits `4` when the hint is `BLOCKED`. Enable **only** the features reported; capabilities do not change mid-session, so probing repeatedly is pure token cost.

## Prompt Card

```text
Capabilities ride along with okf.py pack as a one-line "caps:" header — no separate call.
Only run okf.py capabilities when that line is not "all present" or okf.py may be missing.
Enable only reported features; Brain missing on non-trivial mutate => BLOCKED. No tool assumptions.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- [Extending OKF](extending-okf.md)
