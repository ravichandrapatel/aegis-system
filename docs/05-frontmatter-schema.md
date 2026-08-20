# 5. Frontmatter schema

[← Table of contents](README.md)

Lint (`okf.py lint`) treats YAML frontmatter as the house schema for every durable markdown concept. The target is **OKF v0.2**.

## Minimal required block

```yaml
---
type: Concept          # one of Known types (see 04-document-types.md)
title: Human-readable name
description: One-line summary for indexes and pack/lookup
tags: [kebab-case, topic]
status: stable         # draft | stable | deprecated
generated: { by: okf-agent/cursor, at: 2026-07-13T00:00:00Z }
---
```

> **Superseded:** `timestamp` was the v0.1 date field. OKF v0.2 §13.1 replaces it with `generated.at`, which also records *who* produced the content. Legacy `timestamp` still parses, but new documents MUST NOT use it. Do not invent aliases like `last_modified` at the top level; the kernel will not recognize them.

## Field reference

| Field | Required? | Purpose | Notes |
| --- | --- | --- | --- |
| `type` | **YES** (lint error if missing) | Document class | One of: Concept, Playbook, System, Incident, Reference |
| `title` | House-required (warning if missing) | Human name | Highest-weighted field in lookup ranking |
| `description` | House-required (warning if missing) | One-line summary | Critical for `index.json` / lookup ranking |
| `tags` | Recommended | Discovery keywords | kebab-case; standards use tag `standard` |
| `resource` | Optional; **recommended for `Reference`** | Pointer to the thing described | URL or vault-absolute path — see below |
| `status` | Recommended | Lifecycle | `draft` \| `stable` \| `deprecated`; absent means `stable` (`DBG-314`) |
| `generated` | Recommended | Who produced this, and when | `{ by, at }`; `by` follows the actor convention (`DBG-313`) |
| `verified` | Optional | Who confirmed it | List of `{ by, at }`, or a bare mapping. Drives the trust tier |
| `stale_after` | Optional | Absolute expiry | `YYYY-MM-DD`; stale when `today >= stale_after` (`DBG-315`) |
| `sources` | Optional | Provenance | List of entries, each requiring `resource` (`DBG-316`) |
| `pack_force_when` | Optional | Keyword list that force-includes this card | **House extension.** Matched on **token boundaries** — see below |

Everything above except `pack_force_when` is reserved by the spec. Producers may add their own keys — §4.1 says consumers "MUST NOT reject documents with unrecognized fields" — but reusing a reserved key with an off-spec value is worse than inventing a new one, because consumers will read it and misinterpret.

### Trust: `generated`, `verified`, and tiers

Knowledge in this brain is largely agent-written and then injected as binding Prompt Cards. The trust family makes that visible instead of implied.

```yaml
generated: { by: okf-agent/cursor,  at: 2026-08-21T00:00:00Z }   # who wrote it
verified:  { by: human:ghost,       at: 2026-08-21T09:00:00Z }   # who checked it
```

Actors take one of three forms (§7): `human:<name>`, `process:<name>`, or `<agent>/<model>`. The `human:` prefix is load-bearing — it is what separates a reviewed document from a machine-written one.

| `verified` | Tier | Prompt Card shows |
| --- | --- | --- |
| absent | unverified | `trust: unverified` |
| non-`human:` actors only | machine-confirmed | `trust: machine-confirmed` |
| any `human:` actor | human-reviewed | *(nothing)* |

The tier is **derived at read time, never stored** — a stored verdict goes stale the moment someone re-verifies. Good standing costs zero tokens, so reviewing a document is what removes its label.

### YAML gotcha: reserved indicator characters

Frontmatter is real YAML. Characters YAML reserves must be quoted:

```yaml
pack_force_when: ["@workspace", token bloat]   # correct
pack_force_when: [@workspace, token bloat]     # PARSE ERROR — '@' is reserved
```

The second form shipped in this repo for months because the old hand-rolled parser accepted it. Any conformant consumer would have dropped the document.

### `resource` (pointer to the described thing)

A concept describes something; `resource` says where that something lives.

```yaml
resource: https://docs.example.com/api/orders   # upstream page, console link, dashboard
```

| Behavior | Detail |
| --- | --- |
| Value | An `http(s)://` URL or a vault-absolute path (`/vault/...`). Anything else warns (`DBG-310`) |
| `Reference` concepts | **SHOULD** set it — a cached page with no link back to its source warns (`DBG-311`) |
| `scrape` | Writes it automatically from the fetched URL |
| Pack output | Emitted as a `source:` line under the card, so an agent holding the card can reach the original |
| Ranking | Not scored — it is a pointer, not searchable prose |

### `pack_force_when` (force-include keywords)

A concept listing `pack_force_when` is injected ahead of ranked hits whenever the query matches one of its keywords.

```yaml
pack_force_when: [token, drift, workspace, copilot, context]
```

| Behavior | Detail |
| --- | --- |
| Matching | **Token boundaries**, not substrings. `tab` no longer fires on “table”/“stable”, `deploy` no longer fires on “deployment”. |
| Multi-word keywords | Must appear as a **contiguous phrase** (e.g. `prompt card` matches “prompt card budget”, not “card prompt”). |
| Ranking | Forced hits enter above the relevance floor and are placed before ranked hits; they still consume the 8-card / token budget. |

Use it sparingly: every forced keyword costs budget on every query that mentions it.

### Standards example (real, from the shipped vault)

```yaml
---
type: Concept
title: IDE Context Guardrails
description: Binding rules to stop IDE token bloat and drift — no @workspace, pack-first cards, rg over legacy search.
tags: [standard, okf, tokens, ide, copilot, cursor, drift]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: ["@workspace", token bloat, context drift, ide context, copilot]
---
```

## Prompt Card section (body, not frontmatter)

Binding standards **MUST** include a non-empty `## Prompt Card` section in the markdown body.

| Constraint | Value | Enforced by |
| --- | --- | --- |
| Per-card target | ≤ ~150 tokens (~600 characters) | `okf.py lint` warn `DBG-309`; `okf.py card --max-chars` |
| Pack budget | Max **8** cards; **~1200** token budget | `okf.py` defaults (`--max-cards` / `--budget` on `pack` and `lookup --card`) |

Both pack limits are enforced by the kernel: assembly stops when either is reached, and a single oversized card is truncated to fit.

See [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md).

## What lookup indexes from frontmatter

`okf.py lookup` / `index.json` score against:

- `id` / path (concept id)
- `title`
- `description`
- `tags`
- `type`

**Bodies are not used for ranking** (except as a ripgrep fallback when the index misses entirely). That is intentional: cheap retrieval first.

## Status values — when to use

| `status` | Meaning | Typical action |
| --- | --- | --- |
| `stable` | Current truth | Default for live docs; also the meaning when `status` is absent |
| `draft` | Work in progress | OK in vault; do not rely on it for binding decisions |
| `deprecated` | Superseded | Link to the replacement in the body |

These three are the whole enum (§5.4). `active` is **not** a value — this repo used it until the v0.2 migration. No kernel command filters on `status`; it is a signal for humans and agents.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| No frontmatter / broken `---` fencing | Add valid block; lint reports `DBG-002` |
| Missing `type` | Add known type — lint error |
| Standard without Prompt Card | Add `## Prompt Card` — lint `DBG-308` |
| Encyclopedic `description` | Keep one line; put detail in body |
| Putting binding rules in a plain Concept | Move to `standards/` with tag `standard` |
| Broad `pack_force_when` keywords | Force-includes crowd out ranked hits — keep the list tight |
| Using `timestamp` | Superseded by `generated: { by, at }` (§13.1) |
| `status: active` | Not in the enum — use `stable` (`DBG-314`) |
| Unquoted `@` / `` ` `` in a YAML value | Quote it; these are reserved indicators |
| Bare actor like `by: cursor` | Use `human:<name>`, `process:<name>`, or `<agent>/<model>` (`DBG-313`) |

## Related

- [Document types](04-document-types.md)
- [OKF House Schema](../_okf_knowledge/standards/okf-house-schema.md)
- [Standards](10-standards.md)
