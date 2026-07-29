---
name: okf-writeback
description: >-
  Write Aegis Rung 1 inbox notes for durable learnings or change close-out.
  Use when a write-back trigger fired or the user asks to capture learning to OKF.
---

Capture learning in `_okf_knowledge/_inbox/`. Do not freestyle-edit `vault/` or `standards/` here — that is `okf-maintain`.

## Triggers

user-corrected fact · live-resolved pin/version · root cause found · lookup gap · multi-attempt procedure · non-trivial change close-out

## How to run

Write `_okf_knowledge/_inbox/<YYYY-MM-DD>-<slug>.md`:

```markdown
# Change close-out write-back: <slug>

**Evidence grade:** observed | provided | verified | inferred
**Suggested destination:** vault/... | standards/... | MAINTAIN later | no durable vault candidate

## What shipped / learned
- …
```

## Guardrails

- Rung 1 only in this skill (inbox create).
- If durable + destination clear and compile/lint can finish now → hand off to `okf-maintain`.
- Else leave `MAINTAIN later` in the note.
- Skip when no trigger fired — do not sweep inbox every turn.
