---
applyTo: "_okf_knowledge/**,AGENTS.md"
---

# OKF brain mutations

Brain edits bind to [`vault/playbooks/maintain-okf-system.md`](../../_okf_knowledge/vault/playbooks/maintain-okf-system.md) and [`standards/okf-house-schema.md`](../../_okf_knowledge/standards/okf-house-schema.md).

- Required frontmatter: `type`, `title`, `description`, `tags`, `timestamp`, `status`.
- Files under `standards/` (or tag `standard`) **MUST** include a non-empty `## Prompt Card` (≤ ~600 chars).
- Update affected `index.md` files and `_okf_knowledge/log.md`.
- From package root: `python3 _okf_knowledge/kernel/okf.py compile` then `lint` — must be 0 errors.
- Raw notes land in `_okf_knowledge/_inbox/` first; do not freestyle vault ingest.
