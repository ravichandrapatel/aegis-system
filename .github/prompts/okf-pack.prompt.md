---
name: okf-pack
description: Rule #1 — build OKF Prompt Pack before planning or multi-file edits
agent: agent
argument-hint: task keywords (e.g. capability discovery maintain)
---

Follow the agent skill [okf-pack](../skills/okf-pack/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "${input:keywords:task keywords}"
```

Inject only returned `## Prompt Card` text.
