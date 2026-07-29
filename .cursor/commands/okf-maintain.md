---
name: /okf-maintain
id: okf-maintain
category: Workflow
description: Rung 2 — ingest OKF knowledge via maintain playbook (compile + lint)
---

Follow `.cursor/skills/okf-maintain/SKILL.md`.

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```
