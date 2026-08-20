---
name: okf-maintain
description: >-
  Ingest durable OKF knowledge via the maintain playbook (Rung 2): frontmatter,
  links, compile, lint. Use for MAINTAIN/INGEST or when promoting an inbox note.
---

Follow the playbook end-to-end — do not restate it here.

1. Read [`maintain-okf-system.md`](../../../_okf_knowledge/vault/playbooks/maintain-okf-system.md).
2. Schema: [`okf-house-schema.md`](../../../_okf_knowledge/standards/okf-house-schema.md).
3. From package root, when the checklist reaches compile/lint:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

## Guardrails

- Inbox stays raw until ingest. Checklist incomplete → `MAINTAIN later` (no partial vault edit).
- Destructive vault ops → `mutation-gate` first.
