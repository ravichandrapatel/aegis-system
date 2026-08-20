---
type: Concept
title: Simplicity First (Laziness Ladder)
description: Prefer the simplest, shortest, minimal solution that works — reuse before new files before tooling.
tags: [standard, simplicity, laziness-ladder, principles]
generated: { by: okf-agent/cursor, at: 2026-07-28T00:30:00Z }
status: stable
---

# Laziness Ladder

The design lens applied *after* Rule #1 (Pack First) in [AGENTS.md](/AGENTS.md) — a lens, not a numbered rule. When multiple approaches solve the problem, pick the lowest rung that still works:

| Rung | Approach | Example |
|------|----------|---------|
| 1 | Do nothing new | Reuse an existing concept, playbook, or reference |
| 2 | Edit one file | Fix a link, add one paragraph, patch one script |
| 3 | Add one small file | One new concept — not a new directory tree |
| 4 | Add tooling | Only when manual steps repeat and hurt |
| 5 | Add abstraction | Last resort — never start here |

## In the vault

- One concept per file; cross-link instead of duplicating prose.
- Prefer `index.md` disclosure over bulk-reading the tree.
- Kernel stays stdlib-only unless a dependency is unavoidable.
- New types, directories, or tooling require justification against this ladder.

## In code

- Smallest diff that fixes the root cause — no drive-by refactors.
- Match existing conventions before inventing new ones.

## Prompt Card

```text
Laziness Ladder: reuse → one-file edit → one small file → tooling → abstraction last.
Smallest diff; stdlib kernel; justify new dirs/types.
```

# Related

- DNA: [AGENTS.md](/AGENTS.md)
- Schema: [OKF House Schema](/standards/okf-house-schema.md)
- Prompt discipline: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
