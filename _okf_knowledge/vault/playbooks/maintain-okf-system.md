---
type: Playbook
title: Maintain OKF System
description: Add or update durable OKF knowledge — frontmatter, links, compile, lint.
tags: [okf-system, ingest, maintenance, okf, procedure]
generated: { by: okf-agent/cursor, at: 2026-07-28T00:30:00Z }
status: stable
---

# Trigger

Add or change durable knowledge in this package: standard, concept, playbook, system, reference, or incident.

# Preconditions

- Raw material (if any) is in `_inbox/` and not edited in place.
- You know the `type` and destination directory (table below).
- Schema: [OKF House Schema](/standards/okf-house-schema.md).

# Destination table

| Content | `type` | Directory |
| --- | --- | --- |
| House rule | `Concept` + tag `standard` | `standards/` |
| Evergreen fact | `Concept` | `vault/concepts/` |
| Procedure | `Playbook` | `vault/playbooks/` |
| Running system | `System` | `vault/systems/` |
| Post-mortem | `Incident` | `vault/incidents/` |
| Cached upstream / pins | `Reference` | `vault/references/` |

# Steps

1. Create/update one file with required frontmatter.
2. Standards **MUST** include `## Prompt Card` (≤ ~600 chars).
3. Cross-link both directions; update affected `index.md` files.
4. Append a line to [log.md](/log.md).
5. From **package root** (directory with `AGENTS.md`):

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

6. Lint must report `0 error(s)`. Archive or delete the `_inbox/` source after successful ingest.

# Change close-out write-back

If a non-trivial engineering change learned something durable: write `_inbox/<YYYY-MM-DD>-<slug>.md` (Rung 1). Run this playbook for Rung 2 only when destination is clear and the checklist above can finish; else leave `MAINTAIN later`.

# Verification

- [ ] Frontmatter valid
- [ ] Indexes + cross-links updated
- [ ] `compile` + `lint` clean
- [ ] `log.md` updated

## Prompt Card

```text
Brain mutate: correct type/dir; frontmatter; cross-links; index.md; log.md.
Standards MUST ## Prompt Card. From package root: okf.py compile then lint (0 errors).
Close-out: Rung 1 _inbox; Rung 2 only if this checklist finishes.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [OKF House Schema](/standards/okf-house-schema.md)
- [Extending OKF](/vault/concepts/extending-okf.md)
