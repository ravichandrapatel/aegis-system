---
type: Concept
title: Aegis Capability Discovery
description: Probe Brain/FS/Python/Git/Shell before enabling pack/compile/lint; BLOCKED when Brain missing for non-trivial mutate.
tags: [aegis-system, capability, discovery, portable]
timestamp: 2026-07-28T00:30:00Z
status: active
pack_force_when: [capabilities, capability-discovery, okf.py capabilities]
---

# Aegis Capability Discovery

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Reports present/missing/degraded for Brain, Filesystem, Python, Git, Shell, compile, lint plus `enabled_features` and `runtime_hint` (`READY` | `BLOCKED`). `--strict` exits `4` when blocked.

Run once per non-trivial turn (and on env change). Trivial Q&A may skip. If Python/`okf.py` is missing, probe with shell only — **never** claim a successful Prompt Pack.

Hard rule: non-trivial CREATE/MODIFY with Brain missing → `BLOCKED`.

## Prompt Card

```text
Non-trivial: okf.py capabilities [--json] before pack. Enable only reported features.
Brain missing → BLOCKED for CREATE/MODIFY. No tool assumptions.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [Extending Aegis](/vault/concepts/extending-aegis.md)
- [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
