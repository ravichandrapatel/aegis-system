---
name: code-review
description: Review a diff / branch / PR against the code-review bar and DevOps quality gates
agent: agent
argument-hint: PR number or branch/diff to review
---

Follow the agent skill [code-review](../skills/code-review/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "code review quality gates ${input:stack:stack keywords}"
gh pr diff ${input:target:PR number or branch}
```

Run the quality gates before reading code, then review top-down: design, blast radius, functionality, security, complexity, tests. Write findings as Conventional Comments citing `file:line` and the standard, and close as Approved | Manual Intervention | Blocked.
