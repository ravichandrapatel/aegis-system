---
type: Concept
title: OKF House Schema
description: Required frontmatter and Prompt Card rules for durable Aegis OKF documents.
tags: [standard, okf, schema, frontmatter]
timestamp: 2026-07-28T00:30:00Z
status: active
---

# OKF House Schema

Binding schema for durable docs under `_okf_knowledge/`. Enforced by `okf.py lint` (required `type`; standards Prompt Card gate).

## Required frontmatter

```yaml
---
type: Concept          # Concept | Playbook | System | Reference | Incident
title: Human-readable name
description: One-line summary for indexes and pack/lookup
tags: [kebab-case, topic]
timestamp: 2026-07-28T00:00:00Z   # ISO-8601 UTC
status: active
---
```

| Field | Rule |
| --- | --- |
| `type` | **MUST** — OKF required field |
| `title`, `description` | **MUST** for house docs (lint warns if missing) |
| `tags` | **SHOULD**; house rules under `standards/` **MUST** include tag `standard` |
| `timestamp` | **SHOULD** — UTC `Z` |
| `pack_force_when` | Optional keyword list — pack/lookup force-includes when query matches |

## Prompt Cards

- Binding standards (`standards/` or tag `standard`) **MUST** include a non-empty `## Prompt Card` (lint `DBG-308`).
- Card body **SHOULD** be ≤ ~600 characters (~150 tokens).
- Other agent-facing concepts **SHOULD** ship a card.

## Reserved files

Do not treat as concepts: `index.md`, `log.md` at brain root; compiled `index.json` / `prompt_cards.json` / `graph.json`.

## Prompt Card

```text
Durable OKF docs MUST have YAML frontmatter with type,title,description,tags,timestamp,status.
Standards MUST tag standard and ship ## Prompt Card (≤~600 chars). Lint enforces type + cards.
```

# Related

- Retrieval: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Maintenance: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- DNA: [AGENTS.md](/AGENTS.md)
