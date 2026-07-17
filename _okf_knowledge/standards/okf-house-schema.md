---
type: Concept
title: OKF House Schema
description: Binding document schema for every durable brain concept — known types, required frontmatter, timestamp canon, Prompt Card exceptions, and the OKF v0.2 Code dialect.
tags: [standard, okf, schema, frontmatter, document-types]
timestamp: 2026-07-18T02:45:00Z
status: active
owns: [frontmatter, schema, document-types]
priority: 90
# Force keywords are matched as whole tokens against the query token set (hyphens
# split). Use single tokens only. Never "maintain"/"ingest"/"schema" (steal other cards).
pack_force_when: [frontmatter]
---

# OKF House Schema

Every durable markdown concept under `_okf_knowledge/` **MUST** carry YAML frontmatter. `okf.py lint` enforces this schema — agents **MUST NOT** validate it manually; assume lookup returns validated knowledge.

## Known `type` values

| `type` | Zone | Directory (under `_okf_knowledge/`) |
| --- | --- | --- |
| `Concept` | 3 or 4 | `standards/` (tag `standard`) or `vault/` |
| `Playbook` | 4 | `vault/playbooks/` |
| `System` | 4 | `vault/systems/` |
| `Incident` | 4 | `vault/incidents/` |
| `Reference` | 4 | `vault/references/` |
| `Profile` | 2 | `kernel/profiles/` (optional / schema; not a runtime gate today) |
| `Code` | 5 | `code/` (OKF v0.2 dialect; machine-produced, regenerate-only) |

## Required frontmatter fields

```yaml
---
type: Concept          # one of Known types above
title: Human-readable name
description: One-line summary for indexes and okf_lookup
tags: [kebab-case, topic]
timestamp: 2026-07-13T00:00:00Z
status: active         # active | deprecated | draft
owns: [yaml, metadata] # Standards only: explicit domain ownership (REQUIRED when scopes may overlap)
priority: 100          # Standards only: 1-100 (highest wins conflicts; REQUIRED when scopes may overlap)
---
```

## Field rules

* `type` is **REQUIRED** (lint error if missing).
* `title` and `description` are house-required (lint warning if missing).
* `timestamp` is the kernel's canonical date field (`okf.py enrich`/`optimize` stamp it; recency ranking reads it). It **MUST** be updated (ISO-8601) on every modification — cache invalidation, deterministic tie-breaking, and history tracking depend on it. **MUST NOT** use `last_modified` or other aliases; the kernel will not recognize them.
* Standards (`standards/` path or tag `standard`) **MUST** include a non-empty `## Prompt Card` section (lint `DBG-308`; target ≤600 chars, `DBG-309`).
* Optional Prompt Card exceptions: `prompt_card_max_chars` (per-doc clamp; default 600, hard ceiling 2000) and `pack_force_when: [keywords…]` (force-include in the Prompt Pack when the query matches — bypasses pack max_cards/budget; forced cards capped at 4).

## `type: Code` — OKF v0.2 dialect (Zone 5)

Additionally **REQUIRED** (lint error `DBG-310` if missing):

* `schema_version: 0.2` (mismatch warns `DBG-311`)
* `language` — e.g. `terraform` | `cloudformation` | `bicep` | `shell` | `python` | `go` | `yaml-k8s` | `yaml-ansible` | `yaml`
* `kind` — e.g. `resource` | `module` | `function` | `class` | `manifest` | `play`
* `source` — `relpath:line` back to the described artifact

Optional typed-relationship lists — `depends_on`, `references`, `calls`, `called_by` — map onto the graph edge vocabulary; entries that resolve to concept ids become graph/adjacency edges, others remain metadata. Code concepts are exempt from orphan checks (`DBG-306`) and are regenerate-only (never hand-edited or ingested).

## Placement & verification

Placement, index updates, cross-links, and post-change verification live only in the maintain playbook: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md).

## Prompt Card

```text
OKF house schema (lint-enforced — never validate manually):
types Concept|Playbook|System|Incident|Reference|Profile|Code.
Required: type,title,description,tags,timestamp(ISO-8601, canonical —
NOT last_modified),status. Standards: +owns,+priority,+## Prompt Card
(≤600 chars); optional prompt_card_max_chars / pack_force_when.
Code (v0.2, zone code/): +schema_version 0.2,language,kind,source;
optional depends_on/references/calls/called_by → graph edges;
regenerate-only. Placement/verify: maintain-aegis-system playbook.
```

## Related

- Playbook: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Standard: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Standard: [Metadata headers](/standards/metadata-headers.md)
- Control plane: [AGENTS.md](/AGENTS.md) §1.3 (stub pointer)
