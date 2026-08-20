# 12. Maintenance & ingest

[← Table of contents](README.md)

**Binding procedure:** [`../_okf_knowledge/vault/playbooks/maintain-okf-system.md`](../_okf_knowledge/vault/playbooks/maintain-okf-system.md)

`AGENTS.md` (Brain layout): any add/update/ingest/restructure of durable brain knowledge **MUST** follow that playbook. Do not invent alternate layouts or skip compile/lint/`log.md`.

## When this applies

| Change | Follow maintain playbook? |
| --- | --- |
| New/edited Concept, Playbook, System, Incident, Reference | **Yes** |
| New/edited Standard | **Yes** |
| New/edited kernel `.py` script | **Yes** (scripts section + verify) |
| Protocol change in `AGENTS.md` | **Yes** (control-plane row) |
| Edits only under `docs/` | No brain compile required; keep docs accurate |
| Scratch notes in `_inbox/` only | Not yet — until you **INGEST** |

## Ingest funnel

```
_inbox/  (raw)
   │
   │  classify type (see 04-document-types.md)
   ▼
standards/ | kernel/ | vault/
   │
   ├─ update index.md files
   ├─ bidirectional cross-links
   ├─ append log.md
   ├─ okf.py compile
   └─ okf.py lint  → 0 errors
   │
   ▼
archive/delete inbox source
```

## Post-change checklist (copy/paste)

```bash
# From package directory
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

| Step | Action |
| ---: | --- |
| 1 | Update affected `index.md` files |
| 2 | Cross-link both directions |
| 3 | Append dated entry to `log.md` — the heading is a bare ISO 8601 `YYYY-MM-DD`, no suffixes; same-day work merges into the existing section |
| 4 | Run `okf.py compile` |
| 5 | Run `okf.py lint` — **0 error(s)**; `info` findings (e.g. `DBG-317`) never fail the build |
| 6 | Archive or delete `_inbox/` source after ingest |

Step 2 is not decoration: `compile` turns in-vault markdown links (by convention, the `# Related` section) into `graph.json` edges, and `pack` prints those edges as the `related:` line under each card. A concept nobody links to is unreachable by traversal — and lint reports it as an orphan (`DBG-306`).

## Verification gates

- [ ] Valid frontmatter per [schema](05-frontmatter-schema.md) / [okf-house-schema](../_okf_knowledge/standards/okf-house-schema.md)  
- [ ] Indexes list the new/changed page  
- [ ] Standards include `## Prompt Card`  
- [ ] `Reference` docs set `resource` (lint `DBG-311`), and any `resource` is a URL or vault-absolute path (`DBG-310`)  
- [ ] `status` is in the enum and any `generated` / `verified` actor follows the convention (`DBG-313` / `DBG-314`)  
- [ ] Lint clean  
- [ ] `log.md` updated  
- [ ] Playbook followed end-to-end  

## Extending an empty framework

Starter guide: [`extending-okf.md`](../_okf_knowledge/vault/concepts/extending-okf.md)

Typical growth order (Laziness Ladder friendly):

1. Standards you actually enforce  
2. Domain Concepts/Systems in `vault/` (lookup-discoverable)  
3. Playbooks for repeat procedures  
4. Systems / Incidents / References as operations demand  

## Related

- [Document types](04-document-types.md)
- [Kernel tools](09-kernel-tools.md)
- [Compiled artifacts](07-compiled-artifacts.md)
