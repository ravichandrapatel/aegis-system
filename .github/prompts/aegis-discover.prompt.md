---
name: aegis-discover
description: Capability Discovery — probe Brain/FS/Python/Git before non-trivial work
agent: agent
argument-hint: optional focus (e.g. brain git)
---

Follow the agent skill [aegis-discover](../skills/aegis-discover/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Emit a short Capability Report, then continue only with enabled features.
