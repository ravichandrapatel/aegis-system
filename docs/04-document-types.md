# 4. Document types — when to use what

[← Table of contents](README.md)

Every durable markdown concept under the brain **MUST** declare a `type` in YAML frontmatter. Lint treats missing `type` as an error.

## Known types (protocol §1.3)

| `type` | Zone | Directory (under `_okf_knowledge/`) | Primary job |
| --- | --- | --- | --- |
| `Concept` | 3 or 4 | `standards/` (tag `standard`) or `vault/` | Evergreen knowledge **or** house law |
| `Playbook` | 4 | `vault/playbooks/` | Step-by-step agent procedure |
| `System` | 4 | `vault/systems/` | A running system you operate |
| `Incident` | 4 | `vault/incidents/` | Post-mortem / learning from failure |
| `Reference` | 4 | `vault/references/` | Cached upstream documentation |
| `Module` | 2 | `kernel/modules/` | Core domain execution + artifact ownership |
| `Vendor` | 2 | `kernel/vendors/` | Cloud/tool execution extension |
| `Profile` | 2 | `kernel/profiles/` | Operational context (allowed modules/standards/roles) |

## Decision table (practical)

| You are documenting… | Choose | Put it in | Also update |
| --- | --- | --- | --- |
| Evergreen knowledge, pattern, tool overview | `Concept` | `vault/concepts/` (or domain folder under `vault/`) | `vault/…/index.md` |
| House rule (MUST/SHOULD) | `Concept` + tag `standard` | `standards/` | `standards/index.md` |
| Executable agent procedure | `Playbook` | `vault/playbooks/` | `playbooks/index.md` |
| Cached upstream docs | `Reference` | `vault/references/` | Run `cache_optimizer.py` when applicable |
| Running system in workspace | `System` | `vault/systems/` | `systems/index.md` |
| Post-mortem | `Incident` | `vault/incidents/` | Link systems/playbooks |
| Core execution logic / ownership | `Module` | `kernel/modules/` | `modules/index.md` |
| Cloud/tool execution extension | `Vendor` | `kernel/vendors/` | `vendors/index.md` |
| Who/what is loaded for a role | `Profile` | `kernel/profiles/` | Profile index / schema as you define it |
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

## Deep dive: Module vs Vendor

| | **Module** | **Vendor** |
| --- | --- | --- |
| Scope | Core domain (e.g. Kubernetes patterns your org owns) | Third-party / cloud surface (e.g. AWS EKS specifics) |
| Owns | Triggers, validation rules, **artifact file ownership** | Execution extensions, vendor-specific gates |
| MUST NOT | Become a dumping ground for encyclopedias | Duplicate System/Concept encyclopedias of the product |

**Anti-collision rule**

| Layer | Owns | MUST NOT |
| --- | --- | --- |
| `kernel/vendors/` | Triggers, minimum evidence, execution pipelines, ownership vs modules | Duplicate System/Concept encyclopedias |
| `vault/` | Passive facts, architecture, runbooks, incidents, cached docs | Embed vendor routing/trigger tables |

Cross-link instead: Vendor → System/Concept; System → Vendor.  
On conflict, **vendors beat vault** in knowledge precedence (`AGENTS.md` §2.2).

## Deep dive: Profile

**Use when:** you need a named operational context such as `operator`, `architect`, or `migration`.

Profiles gate the **Capability Registry Check** (`AGENTS.md` §4.1): if a required module/vendor/standard for the profile is missing, Aegis **HALTs** with exit code `4` (Unsupported).

See [Profiles](07-profiles.md).

## Precedence reminder (conflicts)

When two sources disagree:

1. Standards (via Prompt Cards / lookup)
2. Local workspace / `_inbox` / terminal context
3. Vendors
4. Modules
5. Passive vault
6. External OCI/Git metadata

Within overlapping standards/modules: **`owns` list wins**; if both claim the domain, higher **`priority`** wins; identical `owns`+`priority` → **fail closed** (exit `1`).

## Related

- [Frontmatter schema](05-frontmatter-schema.md)
- [Brain zones](03-brain-zones.md)
- [Maintenance](13-maintenance.md)
