# 4. Document types — when to use what

[← Table of contents](README.md)

Every durable markdown concept under the brain **MUST** declare a `type` in YAML frontmatter. Lint treats missing `type` as an error.

`type` says what a document **is**; `status` says where it sits in its lifecycle — `draft` | `stable` | `deprecated`, with absent meaning `stable` (`active` is not a value). The two are independent: see [Frontmatter schema — Status values](05-frontmatter-schema.md#status-values--when-to-use).

## Known types ([okf-house-schema](../_okf_knowledge/standards/okf-house-schema.md))

There are exactly five. `okf.py lint` warns (`DBG-302`) on any `type` outside this taxonomy.

| `type` | Zone | Directory (under `_okf_knowledge/`) | Primary job |
| --- | --- | --- | --- |
| `Concept` | 3 or 4 | `standards/` (tag `standard`) or `vault/` | Evergreen knowledge **or** house law |
| `Playbook` | 4 | `vault/playbooks/` | Step-by-step agent procedure |
| `System` | 4 | `vault/systems/` | A running system you operate |
| `Incident` | 4 | `vault/incidents/` | Post-mortem / learning from failure |
| `Reference` | 4 | `vault/references/` | Cached upstream documentation |

## Decision table (practical)

| You are documenting… | Choose | Put it in | Also update |
| --- | --- | --- | --- |
| Evergreen knowledge, pattern, tool overview | `Concept` | `vault/concepts/` (or domain folder under `vault/`) | `vault/…/index.md` |
| House rule (MUST/SHOULD) | `Concept` + tag `standard` | `standards/` | `standards/index.md` |
| Executable agent procedure | `Playbook` | `vault/playbooks/` | `playbooks/index.md` |
| Cached upstream docs | `Reference` | `vault/references/` | Set `resource`; run `okf.py optimize` when applicable |
| Running system in workspace | `System` | `vault/systems/` | `systems/index.md` |
| Post-mortem | `Incident` | `vault/incidents/` | Link systems/playbooks |
| Vault tooling (lint, compile) | Python script | `kernel/` | Maintain playbook § Scripts |
| Control-plane behavior | Markdown | `AGENTS.md` (package root) | Brain `index.md` if orientation changes |

## Deep dive: Concept

**Use when:** the knowledge is stable and reusable, but not necessarily a procedure.

| Kind of Concept | Location | Extra requirements |
| --- | --- | --- |
| Domain / pattern Concept | `vault/` | Prompt Card **SHOULD** |
| House **standard** | `standards/` | tag `standard`; Prompt Card **MUST** (lint error `DBG-308` without one) |

**Do not use Concept for:** multi-step “do this then that” agent workflows — those are Playbooks.

## Deep dive: Playbook

**Use when:** an agent (or human following the agent) must execute a **procedure**.

Required section skeleton (maintain playbook convention):

```markdown
# Trigger
# Preconditions
# Steps
# Verification
```

**Canonical brain-mutation playbook:** `vault/playbooks/maintain-okf-system.md` — bound by `AGENTS.md` (Brain layout) for **all** durable MAINTAIN/INGEST work.

## Deep dive: System vs Incident vs Reference

| Type | Question it answers | Example |
| --- | --- | --- |
| `System` | What are we running, and how is it shaped? | “prod EKS cluster X” |
| `Incident` | What went wrong, what did we learn? | “2026-07 IRSA outage post-mortem” |
| `Reference` | What did upstream say (cached)? | Scraped AWS docs snapshot |

References are **not** law. Prefer linking; do not paste entire references into generation prompts.

A `Reference` **SHOULD** set [`resource`](05-frontmatter-schema.md#resource-pointer-to-the-described-thing) to the upstream URL it cached — `okf.py scrape` writes it automatically, and lint warns (`DBG-311`) when it is missing. Pack then prints it as the card's `source:` line, so an agent holding a cached page can reach the original.

`scrape` also writes a `sources` provenance entry (each entry **MUST** carry its own `resource`, else `DBG-316`) plus a per-claim markdown footnote keyed to that entry's `id`. That replaces the old `# Citations` body list: in OKF v0.2, provenance lives in frontmatter where a consumer can read it. A freshly scraped `Reference` has no `verified` entry, so its card reads `trust: unverified` until someone confirms it.

## Precedence reminder (conflicts)

> **Convention, not kernel behavior.** Nothing in `okf.py` resolves conflicts between documents. The ordering below is what the agent applies while reasoning; the kernel only ranks and returns cards.

When two sources disagree, `AGENTS.md` resolves in this order:

1. Standards (via Prompt Cards / pack)
2. Local workspace / `_inbox/` / terminal context
3. Passive vault
4. External OCI/Git metadata

At plan time the standard wins and the agent notes the correction. At execution time a conflict with the approved plan fails closed (`PENDING_APPROVAL` or `BLOCKED`) rather than being guessed.

## Related

- [Frontmatter schema](05-frontmatter-schema.md)
- [Brain zones](03-brain-zones.md)
- [Maintenance](12-maintenance.md)
