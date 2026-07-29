---
name: okf-maintain
description: Rung 2 — ingest OKF knowledge via maintain playbook (compile + lint)
agent: agent
argument-hint: inbox note path or topic to ingest
---

Follow the agent skill [okf-maintain](../skills/okf-maintain/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

Lint must report `0 error(s)` before closing ingest.
