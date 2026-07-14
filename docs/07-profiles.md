# 7. Profiles

[← Table of contents](README.md)

Profiles live under `_okf_knowledge/kernel/profiles/` and have frontmatter `type: Profile`.

They define **operational context**: which intents, execution modes, modules, vendors, and standards are in play for a request. Aegis loads a Profile during pre-flight **before** graph traversal or generation.

```
Intent Detection → Load Profile → Capability Check → Context Expansion → Governance → Path A|B|C
```

If something the Profile requires is **MISSING** → **HALT** with exit code **4** (Unsupported).

---

## Table of contents (this page)

1. [Why profiles exist](#1-why-profiles-exist)
2. [Dynamic Profile model](#2-dynamic-profile-model)
3. [Schema template (`_schema.md`)](#3-schema-template-_schemamd)
4. [Frontmatter fields](#4-frontmatter-fields)
5. [Body sections (required shape)](#5-body-sections-required-shape)
6. [How to author a new dynamic Profile](#6-how-to-author-a-new-dynamic-profile)
7. [Examples (filled from the template)](#7-examples-filled-from-the-template)
8. [When to use which Profile](#8-when-to-use-which-profile)
9. [Capability Check checklist](#9-capability-check-checklist)
10. [Profiles vs Modules vs Vendors vs agent files](#10-profiles-vs-modules-vs-vendors-vs-agent-files)
11. [Maintenance](#11-maintenance)

---

## 1. Why profiles exist

Without a Profile, an agent may:

- Load irrelevant vendors or modules
- Skip required standards
- Apply the wrong evidence bar (`assumed` in production)
- Run intents the role is not authorized for

With a Profile, capability is an **explicit allow-list**, not an implied guess.

---

## 2. Dynamic Profile model

Aegis uses a **dynamic Profile** pattern: Profiles are not limited to a fixed trio (`operator` / `architect` / `migration`). You create **role-specific** Profile documents as needed, all following one schema.

| Idea | Meaning |
| --- | --- |
| **Dynamic** | Profile identity (title, tags, allow-lists) is role-specific and authored per persona |
| **Schema-driven** | Every Profile MUST follow [`_schema.md`](../_okf_knowledge/kernel/profiles/_schema.md) |
| **Capability-gated** | Missing listed modules/standards → exit `4` |
| **Intent-scoped** | `Authorized Intents` limit which Path A/B/C intents that persona may run |

| File | Role |
| --- | --- |
| `kernel/profiles/_schema.md` | **Template / contract** for all Profiles (placeholders in `[brackets]`) |
| `kernel/profiles/<role>.md` | Concrete Profile instances (e.g. `architect.md`, `operator.md`, `gha-maintainer.md`) |

`_schema.md` itself is the blueprint. Do **not** treat the unresolved placeholders as a runnable Profile for production work — instantiate a named file from it.

---

## 3. Schema template (`_schema.md`)

Canonical template (shipped):

```yaml
---
type: Profile
title: [Dynamic Role Name]
description: [One-sentence description of the persona's objective]
tags: [profile, dynamic, role-specific-tags]
last_modified: [ISO-8601 Timestamp]
status: active
---
```

Body skeleton from the schema:

```markdown
# Profile: [Dynamic Role Name]

## 1. Profile Objective
[Define the scope, boundaries, and primary goal of this persona. What are they authorized to do?]

## 2. Dynamic Capabilities (RBAC)

### 2.1 Authorized Intents
* `[Intent 1 - e.g., CREATE, REVIEW, OPERATE]`
* `[Intent 2]`

### 2.2 Execution Modes
* `[advisory | generate | enforce]`
* *(Specify if any mode is strictly PROHIBITED for this role)*

### 2.3 Required Core Modules
* `kernel/modules/[module-name].md`
* *(Aegis will HALT if these are missing during the Capability Check)*

### 2.4 Enforced Standards
* `standards/[standard-name].md`
* *(Governance rules that strictly apply to this role's output)*
```

Source of truth: [`_okf_knowledge/kernel/profiles/_schema.md`](../_okf_knowledge/kernel/profiles/_schema.md).

---

## 4. Frontmatter fields

| Field | Required | Purpose |
| --- | --- | --- |
| `type` | **YES** | Must be `Profile` |
| `title` | **YES** | Dynamic role name (human-readable) |
| `description` | **YES** | One-sentence persona objective (also used by lookup/index) |
| `tags` | **YES** | Include `profile` and `dynamic`; add role-specific tags |
| `last_modified` | **YES** | ISO-8601; update on every edit |
| `status` | **YES** | `active` \| `deprecated` \| `draft` |

Example:

```yaml
---
type: Profile
title: Platform Architect
description: Design and generate infrastructure contracts with strict simplicity and Prompt Card discipline.
tags: [profile, dynamic, architect, design]
last_modified: 2026-07-14T00:00:00Z
status: active
---
```

---

## 5. Body sections (required shape)

### §1 Profile Objective

State **scope**, **boundaries**, and **primary goal**. Explicitly say what the persona may and may not do.

### §2 Dynamic Capabilities (RBAC)

| Subsection | Declares | Capability Check use |
| --- | --- | --- |
| **2.1 Authorized Intents** | Allowed intents (`CREATE`, `REVIEW`, `DEPLOY`, `MAINTAIN`, …) | Reject / HALT if user intent is outside the list |
| **2.2 Execution Modes** | `advisory` \| `generate` \| `enforce` (+ any **PROHIBITED** modes) | Constrain how strongly the agent may mutate state |
| **2.3 Required Core Modules** | Paths under `kernel/modules/` | **HALT `4`** if any file missing |
| **2.4 Enforced Standards** | Paths under `standards/` | **HALT `4`** if missing; always load their Prompt Cards into governance |

#### Execution modes (guidance)

| Mode | Meaning |
| --- | --- |
| `advisory` | Recommend only; no artifact writes / no deploy mutations |
| `generate` | May produce configs/code under Path A after approval gate |
| `enforce` | May drive validation blocks / execution plans that change runtime state |

A Profile **SHOULD** list prohibited modes explicitly (e.g. “`enforce` PROHIBITED”).

#### Optional extensions (recommended as you grow)

Not in the minimal `_schema.md`, but useful in concrete Profiles:

| Extra section | Purpose |
| --- | --- |
| Required / allowed **Vendors** | `kernel/vendors/*.md` allow-list |
| Evidence policy | Ban `assumed` for production operator roles |
| Default Prompt Pack seeds | Standards/modules always considered first in eviction order |

---

## 6. How to author a new dynamic Profile

1. Copy [`_schema.md`](../_okf_knowledge/kernel/profiles/_schema.md) → `kernel/profiles/<kebab-role>.md`.  
2. Replace every `[placeholder]`.  
3. Fill **Authorized Intents** from the protocol intent matrix ([Protocol](06-protocol-routing.md)).  
4. List only modules/standards that **must** exist for this role.  
5. Set execution modes and any **PROHIBITED** modes.  
6. Update `last_modified`.  
7. Follow [Maintenance](13-maintenance.md): indexes/log if you add an index entry, then `okf.py compile` + `okf.py lint`.

**Naming:** prefer kebab-case filenames matching the role (`platform-architect.md`, `gha-operator.md`).

---

## 7. Examples (filled from the template)

### Platform Architect (design / generate)

| Field | Example value |
| --- | --- |
| Intents | `CREATE`, `MODIFY`, `EXPLAIN`, `COMPARE`, `REVIEW` |
| Modes | `advisory`, `generate` — **`enforce` PROHIBITED** |
| Modules | domain modules required for design ownership |
| Standards | `simplicity-first`, `okf-prompt-injection`, `metadata-headers` |

### Operator (day-2)

| Field | Example value |
| --- | --- |
| Intents | `OPERATE`, `TROUBLESHOOT`, `REVIEW`, `DEPLOY`, `ROLLBACK` |
| Modes | `advisory`, `enforce` — generate only when explicitly requested |
| Evidence | `assumed` **PROHIBITED** |
| Standards | operational + domain standards |

### Maintainer (brain ingest)

| Field | Example value |
| --- | --- |
| Intents | `MAINTAIN`, `INGEST`, `EXPLAIN` |
| Modes | `generate` (vault edits) — runtime `enforce` **PROHIBITED** |
| Context node | Always `vault/playbooks/maintain-aegis-system.md` |
| Standards | house standards + metadata headers |

These are examples only — author real files from `_schema.md` before relying on them in Capability Checks.

---

## 8. When to use which Profile

| Situation | Profile approach |
| --- | --- |
| Design / CREATE architecture | Architect-style dynamic Profile (`generate`, no `enforce`) |
| DEPLOY / UPGRADE / ROLLBACK | Operator-style Profile with `enforce` allowed |
| Large MIGRATE program | Dedicated migration Profile (stricter standards list) |
| MAINTAIN / INGEST brain edits | Maintainer Profile + maintain playbook |
| REVIEW a PR | Architect or operator Profile depending on design vs runtime focus |
| New specialized role (e.g. GHA releaser) | **Create a new dynamic Profile** from `_schema.md` — do not overload an unrelated role |

If no Profile matches: **do not invent capabilities**. Select the closest explicit Profile or HALT (`3` missing inputs / `4` unsupported).

---

## 9. Capability Check checklist

Before Path A/B/C work:

- [ ] Concrete Profile file exists (not unresolved `_schema.md` placeholders)  
- [ ] Frontmatter `type: Profile` and `status: active`  
- [ ] User intent ∈ **Authorized Intents**  
- [ ] Requested execution mode ∈ allowed modes (and not PROHIBITED)  
- [ ] Every **Required Core Module** path exists  
- [ ] Every **Enforced Standard** path exists and is active  
- [ ] (If declared) vendors exist; evidence policy respected  

Failure on missing required capability → report gaps; exit **4**.

---

## 10. Profiles vs Modules vs Vendors vs agent files

| Artifact | Answers |
| --- | --- |
| **Profile** (dynamic) | *Who* is acting, *which* intents/modes, *which* modules/standards must load? |
| **Module** | *How* does our core domain execute / own artifacts? |
| **Vendor** | *How* does a cloud/tool extend execution? |
| **Agent entrypoint** (future multi-agent split) | *Which* pipeline contract (generate/validate/execute) is in context? |

Profiles and future agent splits are **orthogonal**: e.g. Generate agent + Architect Profile.

---

## 11. Maintenance

| Change | Action |
| --- | --- |
| New Profile from schema | Copy `_schema.md` → fill → compile/lint |
| Edit allow-lists | Bump `last_modified`; re-run capability assumptions in reports |
| Deprecate a role | `status: deprecated`; point successors in Objective |

Brain mutation rules: [Maintenance](13-maintenance.md). Document type row: [Document types](04-document-types.md).

## Related

- Schema file: [`kernel/profiles/_schema.md`](../_okf_knowledge/kernel/profiles/_schema.md)  
- [Protocol & routing](06-protocol-routing.md) § Capability Check  
- [Document types](04-document-types.md)  
- [`AGENTS.md` §4.1](../AGENTS.md)
