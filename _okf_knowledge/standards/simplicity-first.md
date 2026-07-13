---
type: Concept
title: Simplicity First (Rule #1)
description: The Laziness Ladder — always choose the simplest, shortest, minimal solution that works. Overrides complexity in design, code, and vault structure.
tags: [standard, simplicity, laziness-ladder, principles]
timestamp: 2026-07-13T14:30:00Z
status: active
---

**Rule #1.** Apply the Laziness Ladder as the primary lens for every decision in
this vault and in code: the simplest, shortest, most minimal solution that works.

# Laziness Ladder

When multiple approaches solve the problem, pick the lowest rung that still works:

| Rung | Approach | Example |
|------|----------|---------|
| 1 | Do nothing new | Reuse an existing concept, playbook, or reference |
| 2 | Edit one file | Fix a link, add one paragraph, patch one script |
| 3 | Add one small file | One new concept — not a new directory tree |
| 4 | Add tooling | Only when manual steps repeat and hurt |
| 5 | Add abstraction | Last resort — never start here |

# In the vault

- One concept per file; cross-link instead of duplicating prose.
- Prefer `index.md` progressive disclosure over bulk-reading the tree.
- Scripts are stdlib-only unless a dependency is unavoidable.
- New types, directories, or tooling require justification against this rule.

# In code

- Smallest diff that fixes the root cause — no drive-by refactors.
- No helpers for one-liners; no frameworks where a script suffices.
- Match existing conventions before inventing new ones.

## Prompt Card

```text
Rule #1 Laziness Ladder: simplest shortest minimal solution that works.
Prefer reuse → one-file edit → one small file → tooling → abstraction (last).
Smallest diff; stdlib scripts; no new dirs/types without justification.
```

# Related

- All other house standards: [Standards index](index.md)
- Metadata discipline: [Metadata Headers](metadata-headers.md)
- Prompt discipline: [OKF Prompt Injection](okf-prompt-injection.md)
