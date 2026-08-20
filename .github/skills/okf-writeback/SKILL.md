---
name: okf-writeback
description: >-
  Write OKF Rung 1 inbox notes for durable learnings or change close-out.
  Use when a write-back trigger fired or the user asks to capture learning to OKF.
---

<!-- GENERATED FILE — do not edit.
     Source: .cursor/skills/okf-writeback/SKILL.md
     Regenerate: python3 tools/sync_skills.py -->
Rung 1 only — inbox create. Triggers and DNA: [`AGENTS.md`](../../../AGENTS.md) §1.2. Vault/standards edits → `okf-maintain`.

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

- Durable + clear destination + compile/lint can finish → hand off `okf-maintain`; else `MAINTAIN later`.
- Skip when no trigger fired.
