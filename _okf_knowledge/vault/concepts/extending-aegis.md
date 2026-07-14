---
type: Concept
title: Extending Aegis
description: How to grow this empty framework with your own modules, vendors, standards, and vault knowledge.
tags: [aegis-system, getting-started, framework]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Extending Aegis

This package is an **empty control plane**: `AGENTS.md` + `_okf_knowledge/`. Zip it, drop the folder into an IDE agents directory, then add your knowledge.

## Add durable knowledge

1. Drop raw material in [`_inbox/`](/_inbox/).
2. Follow [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md).
3. From the package directory:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

## Where things go

| Content | Directory (under `_okf_knowledge/`) | `type` |
| :--- | :--- | :--- |
| House rule | `standards/` | `Concept` + tag `standard` |
| Evergreen fact / pattern | `vault/concepts/` | `Concept` |
| Procedure | `vault/playbooks/` | `Playbook` |
| Running system | `vault/systems/` | `System` |
| Post-mortem | `vault/incidents/` | `Incident` |
| Cached upstream docs | `vault/references/` | `Reference` |
| Execution logic | `kernel/modules/` | `Module` |
| Cloud/tool extension | `kernel/vendors/` | `Vendor` |

## Frontmatter (required)

```yaml
---
type: Concept
title: Human-readable name
description: One-line summary for indexes and okf_lookup
tags: [kebab-case, topic]
timestamp: 2026-07-13T00:00:00Z
status: active
---
```

## Prompt Card

```text
New knowledge MUST: pick type/dir from the table (standards/, vault/*, kernel/*),
add required frontmatter (type,title,description,tags,timestamp,status),
then run okf.py compile + okf.py lint from the package dir.
Follow vault/playbooks/maintain-aegis-system.md end-to-end.
```

## Related

- Control plane: [AGENTS.md](/AGENTS.md)
- Maintenance: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Law: [Simplicity First](/standards/simplicity-first.md)
- Architecture ADR (package root, outside vault): see `ADR.md` next to `README.md`
