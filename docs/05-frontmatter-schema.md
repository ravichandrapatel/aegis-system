# 5. Frontmatter schema

[← Table of contents](README.md)

Lint (`okf.py lint`) treats YAML frontmatter as the house schema for every durable markdown concept.

## Minimal required block

```yaml
---
type: Concept          # one of Known types (see 04-document-types.md)
title: Human-readable name
description: One-line summary for indexes and okf_lookup
tags: [kebab-case, topic]
last_modified: 2026-07-13T00:00:00Z
status: active         # active | deprecated | draft
---
```

> **Note:** Older starter docs may still use `timestamp:` instead of `last_modified:`. Prefer **`last_modified`** going forward per protocol §1.3. When editing a file, update the ISO-8601 timestamp.

## Field reference

| Field | Required? | Purpose | Notes |
| --- | --- | --- | --- |
| `type` | **YES** (lint error if missing) | Document class | One of: Concept, Playbook, System, Incident, Reference, Module, Vendor, Profile |
| `title` | House-required (warning if missing) | Human name | Shown in indexes and lookup listings |
| `description` | House-required (warning if missing) | One-line summary | Critical for `index.json` / lookup ranking |
| `tags` | Recommended | Discovery keywords | kebab-case; standards use tag `standard` |
| `last_modified` | Protocol MUST on modification | Cache invalidation, tie-break, history | ISO-8601 |
| `status` | Recommended | Lifecycle | `active` \| `deprecated` \| `draft` |
| `owns` | **REQUIRED for Standards** | Domain ownership claims | Used in conflict resolution |
| `priority` | **REQUIRED for Standards** | Conflict weight | Integer 1–100; higher wins |

### Standards-only example

```yaml
---
type: Concept
title: Simplicity First (Rule #1)
description: Laziness Ladder — simplest solution that works.
tags: [standard, simplicity, principles]
last_modified: 2026-07-13T14:30:00Z
status: active
owns: [design, vault-structure, kernel-scripts]
priority: 100
---
```

## Prompt Card section (body, not frontmatter)

Binding standards **MUST** include a non-empty `## Prompt Card` section in the markdown body.

| Constraint | Value | Enforced by |
| --- | --- | --- |
| Per-card target | ≤ ~150 tokens (~600 characters) | `okf.py lint` warn `DBG-309`; `okf.py card --max-chars` |
| Pack budget (protocol) | Max **8** cards; ~**1200** tokens advisory | `AGENTS.md` §4.2; `okf.py lookup --max-cards` / `--budget` |

See [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md).

## What lookup indexes from frontmatter

`okf_lookup` / `index.json` score against:

- `id` / path (concept id)
- `title`
- `description`
- `tags`
- `type`

**Bodies are not used for ranking.** That is intentional: cheap retrieval first.

## Status values — when to use

| `status` | Meaning | Typical action |
| --- | --- | --- |
| `active` | Current truth | Default for live docs |
| `draft` | Work in progress | OK in vault; avoid relying on in production Profiles |
| `deprecated` | Superseded | Prefer `supersedes` graph semantics when modeled; link to replacement |

## Common mistakes

| Mistake | Fix |
| --- | --- |
| No frontmatter / broken `---` fencing | Add valid block; lint reports `DBG-002` |
| Missing `type` | Add known type — lint error |
| Standard without Prompt Card | Add `## Prompt Card` — lint `DBG-308` |
| Encyclopedic `description` | Keep one line; put detail in body |
| Putting execution triggers in a Concept | Move to Module/Vendor |

## Related

- [Document types](04-document-types.md)
- [`AGENTS.md` §1.3](../AGENTS.md)
- [Standards](11-standards.md)
