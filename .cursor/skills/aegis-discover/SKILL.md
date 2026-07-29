---
name: aegis-discover
description: >-
  Run Aegis Capability Discovery before non-trivial work. Use when starting a
  task, after environment change, or when unsure whether Brain/Git/Python exist.
---

Probe what exists. Do not assume tools. Enable only reported features.

## How to run

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```

Emit a short Capability Report: each cap status + `enabled_features` + `runtime_hint`.

| Cap missing | Disable | Still allow |
| --- | --- | --- |
| FS / Shell | Mutations | Explain-only with pasted context |
| Python / Brain | Pack, compile, lint, ingest | `BLOCKED` for non-trivial CREATE/MODIFY |
| Git | Commit / PR | Edits + pack if Brain OK |
| compile / lint | Rung 2 maintain | Rung 1 `_inbox/` + `MAINTAIN later` |

## Guardrails

- Hard rule: non-trivial CREATE/MODIFY with Brain missing → `BLOCKED`. Do not freestyle.
- Fallback if `okf.py` unavailable: probe `_okf_knowledge/`, `command -v git`, writable cwd; **MUST NOT** claim a successful Prompt Pack.
- Trivial typo/rename/one-path Q may skip discovery.
- Next: `okf-pack` when Brain is present.
