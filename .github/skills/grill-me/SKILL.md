---
name: grill-me
description: >-
  Interview the user about a plan until shared understanding. Use when the user
  asks to grill a design, or after OKF pack when branching decisions remain.
---

<!-- GENERATED FILE — do not edit.
     Source: .cursor/skills/grill-me/SKILL.md
     Regenerate: python3 tools/sync_skills.py -->
Interview me about every material branch of this plan until we share an understanding. One question per turn. Always give your recommended answer. If the codebase or OKF pack already answers it, explore instead of asking.

## How to run

1. Ground first (non-trivial):

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<plan keywords>"
```

2. Walk scope, non-goals, interfaces, failure modes, security/risk, rollout.
3. Stop with a short decision bullet list. Do not implement while grilling.

## Guardrails

- Prefer pack + corpus over interrogation.
- Capture decisions only — no multi-file edits during grill.
