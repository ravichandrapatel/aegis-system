---
type: Concept
title: Aegis Capability Discovery
description: Probe Brain/FS/Python/Git/Shell before enabling pack/compile/lint; BLOCKED when Brain missing for non-trivial mutate.
tags: [aegis-system, capability, discovery, portable]
timestamp: 2026-07-30T18:00:00Z
status: active
pack_force_when: [capabilities, capability-discovery, okf.py capabilities]
---

# Aegis Capability Discovery

Binding policy (disable table, fallbacks, hard `BLOCKED` rule): **[`AGENTS.md`](/AGENTS.md)** § Capability Discovery. Skill recipe: `aegis-discover`.

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Run once per non-trivial turn (and on env change). Trivial Q&A may skip. Enable **only** features the report lists.

## Prompt Card

```text
Non-trivial: okf.py capabilities [--json] before pack. Enable only reported features.
Disable table + BLOCKED rules: AGENTS.md § Capability Discovery. No tool assumptions.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- [Extending Aegis](extending-aegis.md)
