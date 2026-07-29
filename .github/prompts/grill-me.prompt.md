---
name: grill-me
description: Interview about a plan until shared understanding
agent: agent
argument-hint: plan topic or paste the plan
---

Follow the agent skill [grill-me](../skills/grill-me/SKILL.md).

Ground first when non-trivial:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "${input:keywords:plan keywords}"
```

One question per turn with a recommended answer. Do not implement while grilling.
