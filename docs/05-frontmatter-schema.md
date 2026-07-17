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
timestamp: 2026-07-13T00:00:00Z
status: active         # active | deprecated | draft
---
```

> **Note:** `timestamp` is the kernel's canonical date field per [okf-house-schema](../_okf_knowledge/standards/okf-house-schema.md) (AGENTS.md §1.3 points there) — `enrich`/`optimize` stamp it and recency ranking reads it. Do **not** use `last_modified` or other aliases; the kernel will not recognize them. Update the ISO-8601 value on every modification.

## Field reference

| Field | Required? | Purpose | Notes |
| --- | --- | --- | --- |
| `type` | **YES** (lint error if missing) | Document class | One of: Concept, Playbook, System, Incident, Reference, Profile, Code |
| `title` | House-required (warning if missing) | Human name | Shown in indexes and lookup listings |
| `description` | House-required (warning if missing) | One-line summary | Critical for `index.json` / lookup ranking |
| `tags` | Recommended | Discovery keywords | kebab-case; standards use tag `standard` |
| `timestamp` | Protocol MUST on modification | Cache invalidation, tie-break, history | ISO-8601; aliases like `last_modified` are not recognized |
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
timestamp: 2026-07-13T14:30:00Z
status: active
owns: [design, vault-structure, kernel-scripts]
priority: 100
---
```

### Code concepts (OKF v0.2, Zone 5 `code/`)

`type: Code` documents additionally require (lint **error** `DBG-310` if missing):

| Field | Purpose | Example |
| --- | --- | --- |
| `schema_version` | OKF dialect version | `0.2` (warning `DBG-311` if other) |
| `language` | Source language | `terraform` \| `cloudformation` \| `bicep` \| `shell` \| `python` \| `go` \| `yaml-k8s` \| `yaml-ansible` \| `yaml` |
| `kind` | Artifact kind | `resource` \| `module` \| `function` \| `class` \| `manifest` \| `play` |
| `source` | Back-reference to the artifact | `infra/eks.tf:42` |

Optional typed relationships (`depends_on`, `references`, `calls`, `called_by`) are frontmatter lists; entries resolving to concept ids become graph/adjacency edges. Code concepts are exempt from orphan warnings (`DBG-306`) and are never touched by `enrich`/`optimize` — regenerate the zone externally instead.

```yaml
---
type: Code
title: aws_eks_cluster.main
description: EKS cluster resource for the platform workload.
tags: [terraform, eks, code]
timestamp: 2026-07-18T00:00:00Z
status: active
schema_version: 0.2
language: terraform
kind: resource
source: infra/eks.tf:42
depends_on: [code/infra/vpc/aws_vpc.main]
---
```

## Prompt Card section (body, not frontmatter)

Binding standards **MUST** include a non-empty `## Prompt Card` section in the markdown body.

| Constraint | Value | Enforced by |
| --- | --- | --- |
| Per-card target | ≤ ~150 tokens (~600 characters) | `okf.py lint` warn `DBG-309`; `okf.py card --max-chars` |
| Pack budget (protocol) | Max **8** cards; target ≈**1200** tokens (guidance) | `AGENTS.md` §4.2; `okf.py lookup --max-cards` / `--budget` |

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
| Putting binding rules in a plain Concept | Move to `standards/` with tag `standard` |

## Related

- [Document types](04-document-types.md)
- [OKF House Schema](../_okf_knowledge/standards/okf-house-schema.md) (AGENTS.md §1.3 stub)
- [Standards](11-standards.md)
