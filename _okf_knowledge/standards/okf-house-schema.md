---
type: Concept
title: OKF House Schema
description: Required frontmatter and Prompt Card rules for durable OKF documents.
tags: [standard, okf, schema, frontmatter]
generated: { by: okf-agent/cursor, at: 2026-07-28T00:30:00Z }
status: stable
---

# OKF House Schema

Binding schema for durable docs under `_okf_knowledge/`, targeting **OKF**. Enforced by `okf.py lint` (required `type`; standards Prompt Card gate; trust-family shape).

## Required frontmatter

```yaml
---
type: Concept          # Concept | Playbook | System | Reference | Incident
title: Human-readable name
description: One-line summary for indexes and pack/lookup
tags: [kebab-case, topic]
status: stable                                              # draft | stable | deprecated
generated: { by: okf-agent/cursor, at: 2026-07-28T00:00:00Z }
---
```

Reserved by the spec: `type`, `title`, `description`, `resource`, `tags`, plus the `generated` / `verified` / `status` / `stale_after` / `sources` families. House extension: `pack_force_when` only.

| Field | Rule |
| --- | --- |
| `type` | **MUST** — the one field OKF requires |
| `title`, `description` | **MUST** for house docs (lint warns if missing) |
| `tags` | **SHOULD**; house rules under `standards/` **MUST** include tag `standard` |
| `resource` | Optional URL or vault-absolute path to the thing this concept describes. `Reference` concepts **SHOULD** set it (`DBG-311`); a non-URL, non-absolute value warns (`DBG-310`). `scrape` writes it |
| `status` | **SHOULD** — `draft` \| `stable` \| `deprecated`. Absent means `stable`. Any other value warns (`DBG-314`) |
| `generated` | **SHOULD** — `{ by, at }`. `by` **MUST** follow the actor convention (`DBG-313`) |
| `verified` | Optional list (or a bare mapping) of `{ by, at }` confirmations |
| `stale_after` | Optional `YYYY-MM-DD`. Past that date the content is stale (`DBG-315`) |
| `sources` | Optional provenance list; each entry **MUST** carry `resource` (`DBG-316`) |
| `pack_force_when` | House extension. Keyword list — pack force-includes when the query matches on **token boundaries** (multi-word keywords must match as a contiguous phrase). Prefer distinctive terms; a common English word will fire on unrelated queries |

`timestamp` is **superseded** by `generated.at`. It still parses for legacy documents, but new work MUST NOT use it.

## Trust is derived, never stored

Most knowledge here is written by agents and then injected as binding cards. The spec's answer is to record *who* and let the consumer judge:

| `verified` | Tier | Card shows |
| --- | --- | --- |
| absent | unverified | *(nothing — silent default)* |
| non-`human:` actors only | machine-confirmed | `trust: machine-confirmed` |
| any `human:<name>` actor | human-reviewed | *(nothing)* |

Actors follow one form: `human:<name>`, `process:<name>`, or `<agent>/<model>`. Unverified is silent so an all-agent vault does not tax every pack; machine-confirmed and stale still warn. Human review keeps the card quiet.

## Cross-links are load-bearing

Links are not decoration. `compile` turns **every in-vault markdown link in the body** into a `graph.json` edge — a `# Related` section is the house convention for making them deliberate — and `pack` prints each card's neighbours as a `related:` line so the agent can traverse on to concepts the ranked pack did not include. A concept nothing links to is unreachable by traversal; lint flags orphans (`DBG-306`).

## Prompt Cards

- Binding standards (`standards/` or tag `standard`) **MUST** include a non-empty `## Prompt Card` (lint `DBG-308`).
- Card body **SHOULD** be ≤ ~600 characters (~150 tokens).
- Other agent-facing concepts **SHOULD** ship a card.

## Frontmatter parsing

Frontmatter is real YAML, parsed by PyYAML when it is importable. **Without PyYAML** the kernel falls back to a flat subset — `key: value`, inline `key: [a, b]`, block lists — which cannot represent the nested families, so those documents are reported unparseable (`DBG-002`) rather than silently mangled. `okf.py capabilities` reports which path is live; the `nested_yaml` feature flag means the full parser is available.

Quote scalars YAML reserves. `pack_force_when: [@workspace]` is invalid — `@` is a reserved indicator — and must be written `["@workspace"]`.

## Reserved files

Do not treat as concepts: `index.md`, `log.md` at brain root; compiled `index.json` / `prompt_cards.json` / `graph.json`. `index.md` at the bundle root carries **only** `okf_version` in frontmatter; `log.md` date headings **MUST** be bare ISO 8601 `YYYY-MM-DD`.

## Prompt Card

```text
Durable OKF docs MUST have YAML frontmatter: type (required), title, description, tags,
status (draft|stable|deprecated), generated {by,at}. Do not use timestamp — use generated.at.
Actors: human:<name> | process:<name> | <agent>/<model>. Quote YAML-reserved chars like "@x".
Standards MUST tag standard and ship ## Prompt Card (≤~600 chars). Lint enforces type + cards.
```

# Related

- Retrieval: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Maintenance: [Maintain OKF System](/vault/playbooks/maintain-okf-system.md)
- DNA: [AGENTS.md](/AGENTS.md)
