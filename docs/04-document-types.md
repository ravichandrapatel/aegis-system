# 4. Document types — when to use what

[← Table of contents](README.md)

Every durable markdown concept under the brain **MUST** declare a `type` in YAML frontmatter. Lint treats missing `type` as an error.

## Known types ([okf-house-schema](../_okf_knowledge/standards/okf-house-schema.md); AGENTS.md §1.3 stub)

| `type` | Zone | Directory (under `_okf_knowledge/`) | Primary job |
| --- | --- | --- | --- |
| `Concept` | 3 or 4 | `standards/` (tag `standard`) or `vault/` | Evergreen knowledge **or** house law |
| `Playbook` | 4 | `vault/playbooks/` | Step-by-step agent procedure |
| `System` | 4 | `vault/systems/` | A running system you operate |
| `Incident` | 4 | `vault/incidents/` | Post-mortem / learning from failure |
| `Reference` | 4 | `vault/references/` | Cached upstream documentation |
| `Profile` | 2 | `kernel/profiles/` | Dynamic role context from `_schema.md` (intents, modes, standards) |
| `Code` | 5 | `code/` | OKF v0.2 code fact (machine-produced, regenerate-only) |

## Decision table (practical)

| You are documenting… | Choose | Put it in | Also update |
| --- | --- | --- | --- |
| Evergreen knowledge, pattern, tool overview | `Concept` | `vault/concepts/` (or domain folder under `vault/`) | `vault/…/index.md` |
| House rule (MUST/SHOULD) | `Concept` + tag `standard` | `standards/` | `standards/index.md` |
| Executable agent procedure | `Playbook` | `vault/playbooks/` | `playbooks/index.md` |
| Cached upstream docs | `Reference` | `vault/references/` | Run `okf.py optimize` when applicable |
| Running system in workspace | `System` | `vault/systems/` | `systems/index.md` |
| Post-mortem | `Incident` | `vault/incidents/` | Link systems/playbooks |
| Who/what is loaded for a role | `Profile` | `kernel/profiles/` | Profile index / schema as you define it |
| Code artifact fact (resource, function, manifest) | `Code` | `code/` (external producer writes it) | Nothing by hand — regenerate the zone |
| Vault tooling (lint, compile) | Python script | `kernel/` | Maintain playbook § Scripts |
| Control-plane behavior | Markdown | `AGENTS.md` (package root) | Brain `index.md` if orientation changes |

## Deep dive: Concept

**Use when:** the knowledge is stable and reusable, but not necessarily a procedure.

| Kind of Concept | Location | Extra requirements |
| --- | --- | --- |
| Domain / pattern Concept | `vault/` | Prompt Card **SHOULD** |
| House **standard** | `standards/` | tag `standard`; Prompt Card **MUST**; `owns` + `priority` **REQUIRED** (protocol) |

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

**Canonical brain-mutation playbook:** `vault/playbooks/maintain-aegis-system.md` — bound by `AGENTS.md` §1.2 for **all** durable MAINTAIN/INGEST work.

## Deep dive: System vs Incident vs Reference

| Type | Question it answers | Example |
| --- | --- | --- |
| `System` | What are we running, and how is it shaped? | “prod EKS cluster X” |
| `Incident` | What went wrong, what did we learn? | “2026-07 IRSA outage post-mortem” |
| `Reference` | What did upstream say (cached)? | Scraped AWS docs snapshot |

References are **not** law. Prefer linking; do not paste entire references into generation prompts.

> **Retired types:** `Module` / `Vendor` kernel registries no longer exist (`AGENTS.md` §1.1 / §4.1 — "no separate Module/Vendor runtime registry"). Domain knowledge lives under `standards/` and `vault/` and loads via OKF lookup.

## Deep dive: Profile

**Use when:** you need a named **dynamic** operational context (any role), authored from `kernel/profiles/_schema.md`.

Profiles are optional capability templates (schema-only today): authorized intents, execution modes, and enforced standards. The runtime capability check is `AGENTS.md` §4.1 — required standards/evidence from the Prompt Pack present, else **HALT** exit code `4` (Unsupported).

See [Profiles](07-profiles.md) for the full dynamic schema, RBAC sections, and authoring steps.

## Precedence reminder (conflicts)

When two sources disagree (`AGENTS.md` §2.2):

1. Standards (via Prompt Cards / lookup)
2. Local workspace / `_inbox` / terminal context
3. Passive vault
4. Code facts (`code/`, OKF v0.2)
5. External OCI/Git metadata

Within overlapping standards: **`owns` list wins**; if both claim the domain, higher **`priority`** wins; identical `owns`+`priority` → **fail closed** (exit `1`).

## Related

- [Frontmatter schema](05-frontmatter-schema.md)
- [Brain zones](03-brain-zones.md)
- [Maintenance](13-maintenance.md)
