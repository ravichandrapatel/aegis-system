---
name: mutation-gate
description: >-
  Halt for explicit user approval on high-risk mutations (OKF PENDING_APPROVAL).
  Use before IAM/secrets/prod deploy, destructive ops, or multi-file contract rewrites.
---

Enter Runtime State `PENDING_APPROVAL`. Do not apply the gated change until the user explicitly approves.

## When this fires

- IAM / secrets / authz / production deploy or upgrade
- Destructive or irreversible change (delete, deprecate, rollback of live state)
- Multi-file contract rewrite / new layout with blast radius beyond one file
- User or standard requires approval

## How to run

1. State clearly: **Mutation Gate** — what will change, blast radius, rollback path.
2. List gated steps as checkboxes with **`[MUTATION GATE]`**.
3. Stop. Wait for explicit approval (not implied by “continue coding”).
4. After approval → apply only the approved scope; then `okf-writeback` if a trigger fired.

## Guardrails

- No latch for EXPLAIN/COMPARE, docs-only, or low-blast single-file edits with clear evidence.
- Rung 1 inbox write-back does not require this gate; destructive vault ops still do.
- Fail closed if mid-apply discovery conflicts with the approved plan.
