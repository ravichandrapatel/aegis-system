---
name: okf-review
description: >-
  Path B validation — review artifacts or runtime evidence against OKF standards
  via Prompt Pack. Use for REVIEW, OPERATE, TROUBLESHOOT, or when asked to audit.
---

Validate; do not freestyle-mutate production or vault unless the user asks and gates allow.

## How to run

1. Pack with review keywords — the `caps:` header confirms the environment, so there is no separate discovery step:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<review keywords>"
```

2. Compare the artifact / evidence to Prompt Cards (MUST/SHOULD/FORBIDDEN). If the pack is empty, say so plainly and review against general engineering standards — do not imply the vault backed a finding that it did not.
3. Grade evidence: `verified` > `observed` > `provided` > `inferred` (never ship `assumed` for prod advice).
4. Decision: **Approved** | **Manual Intervention** | **Blocked** — with findings tied to standard/card ids when possible.

## Output (compact)

```markdown
### Architectural Review: [Target]
**1. Objective** …
**2. Decision** Approved | Manual | Blocked + key findings
**3. Rollback** cmd or N/A
```

## Guardrails

- Prefer cards over grepping the whole vault for compliance.
- Authoring-time: do not mine graders to invent compliance; explaining a failure may open the cited rule.
- If fix requires high-risk mutate → `mutation-gate` before apply.
