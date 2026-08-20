---
name: /code-review
id: code-review
category: Workflow
description: Review a diff / branch / PR against the code-review bar and DevOps quality gates
---

Follow `.cursor/skills/code-review/SKILL.md`.

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "code review quality gates <stack keywords>"
git diff main...HEAD          # or: gh pr diff <n>
```

Gates first, then top-down review. Findings as Conventional Comments citing `file:line`; close as Approved | Manual Intervention | Blocked.
