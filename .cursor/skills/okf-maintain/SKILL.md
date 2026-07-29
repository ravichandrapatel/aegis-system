---
name: okf-maintain
description: >-
  Ingest durable OKF knowledge via the maintain playbook (Rung 2): frontmatter,
  links, compile, lint. Use for MAINTAIN/INGEST or when promoting an inbox note.
---

Mutate the brain only through the maintain playbook. Schema: `_okf_knowledge/standards/okf-house-schema.md`.

## How to run

1. Read `_okf_knowledge/vault/playbooks/maintain-aegis-system.md`.
2. Destination table: standards / concepts / playbooks / systems / incidents / references.
3. Create/update one file with required frontmatter; standards **MUST** ship `## Prompt Card`.
4. Cross-link both directions; update affected `index.md`; append `_okf_knowledge/log.md`.
5. From package root:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

6. Lint must report `0 error(s)`. Archive or delete the `_inbox/` source after successful ingest.

## Guardrails

- Raw material stays in `_inbox/` until ingest — do not edit inbox notes in place as the durable record.
- If checklist cannot finish → leave inbox as `MAINTAIN later`; no partial vault edit.
- Destructive vault ops → `mutation-gate` first.
