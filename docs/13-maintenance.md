# 13. Maintenance & ingest

[← Table of contents](README.md)

**Binding procedure:** [`../_okf_knowledge/vault/playbooks/maintain-aegis-system.md`](../_okf_knowledge/vault/playbooks/maintain-aegis-system.md)

`AGENTS.md` §1.2: any add/update/ingest/restructure of durable brain knowledge **MUST** follow that playbook. Do not invent alternate layouts or skip compile/lint/`log.md`.

## When this applies

| Change | Follow maintain playbook? |
| --- | --- |
| New/edited Concept, Playbook, System, Incident, Reference | **Yes** |
| New/edited Standard | **Yes** |
| New/edited Module, Vendor, Profile | **Yes** |
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
| 3 | Append dated entry to `log.md` |
| 4 | Run `okf.py compile` |
| 5 | Run `okf.py lint` — **0 error(s)** |
| 6 | Archive or delete `_inbox/` source after ingest |

## Verification gates

- [ ] Valid frontmatter per [schema](05-frontmatter-schema.md) / `AGENTS.md` §1.3  
- [ ] Indexes list the new/changed page  
- [ ] Standards include `## Prompt Card`  
- [ ] Lint clean  
- [ ] `log.md` updated  
- [ ] Playbook followed end-to-end  

## Extending an empty framework

Starter guide: [`extending-aegis.md`](../_okf_knowledge/vault/concepts/extending-aegis.md)

Typical growth order (Laziness Ladder friendly):

1. Standards you actually enforce  
2. One Module + optional Vendor for your domain  
3. Profiles that allow-list those capabilities  
4. Playbooks for repeat procedures  
5. Systems / Incidents / References as operations demand  

## Related

- [Document types](04-document-types.md)
- [Kernel tools](10-kernel-tools.md)
- [Compiled artifacts](08-compiled-artifacts.md)
