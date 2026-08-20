---
name: okf-review
description: Path B — review artifacts against OKF Prompt Pack / standards
agent: agent
argument-hint: review target and keywords
---

Follow the agent skill [okf-review](../skills/okf-review/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "${input:keywords:review keywords}"
```

Decide Approved | Manual | Blocked with findings tied to Prompt Cards.
