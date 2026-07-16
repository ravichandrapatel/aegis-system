---
type: Concept
title: GHA Commit Subjects
description: Ticket-prefixed conventional commit subjects required for hooks and SemVer bumps.
tags: [standard, github-actions, commits, semver]
timestamp: 2026-07-13T16:00:00Z
status: active
---

# GHA Commit Subjects

House rules for subjects in `gha-reusable-actions-workflows`. Enforced by `policies/scripts/commit_message_lib.sh` (global `commit-msg` hook) and Release Manager SemVer.

## MUST

1. Subject **MUST** start with a ticket: `sctask<number>`, `inc<number>`, or `DCDT-<number>` (case-insensitive). Optional `:` after ticket.
2. Subject **MUST** use a keyword: `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `style`.
3. Subject **MUST** match one of the four supported ticket+keyword formats documented in the repo README.
4. Empty subjects **MUST** fail validation.
5. A `release` **MUST** include at least one `feat`, `fix`, or `chore` since the last component tag (or release fails).

## SHOULD

1. Dependabot commits **SHOULD** use prefix `DCDT-0000 chore`.

## Exemptions

- Merge commits (`Merge ...`) **MUST** be exempt from validation.

## SemVer mapping

| Keyword | Bump |
| :--- | :--- |
| `feat` | Minor |
| `fix`, `chore` | Patch |
| `docs`, `refactor`, `perf`, `test`, `style` | None |

## Prompt Card

```text
Commit subject MUST:
- ticket prefix: sctaskN | incN | DCDT-N (optional :)
- keyword: feat|fix|chore|docs|refactor|perf|test|style
- empty subject fails; Merge commits exempt
- Dependabot SHOULD: DCDT-0000 chore
SemVer: feat=minor; fix|chore=patch; docs|refactor|perf|test|style=none
Release needs ≥1 feat|fix|chore since last tag
```

## Related

- Concept: [SemVer from commits](/vault/concepts/semver-from-commits.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Standard: [Simplicity First](/standards/simplicity-first.md), [OKF Prompt Injection](/standards/okf-prompt-injection.md)
