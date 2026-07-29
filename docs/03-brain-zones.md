# 3. Brain zones

[← Table of contents](README.md)

Aegis maps all brain operations to a **5-zone** tree under `_okf_knowledge/`. Zones encode **lifecycle and authority**: scratch vs law vs execution vs passive memory vs machine-produced code facts.

Bundle-absolute links inside the brain (e.g. `/vault/...`, `/standards/...`) are resolved relative to `_okf_knowledge/`.

## Zone map

```
_okf_knowledge/
├── _inbox/          Zone 1 — Untriaged
├── kernel/          Zone 2 — Execution
│   ├── profiles/
│   └── *.py
├── standards/       Zone 3 — Governance
├── vault/           Zone 4 — Knowledge
│   ├── concepts/
│   ├── playbooks/
│   ├── systems/
│   ├── incidents/
│   └── references/
└── code/            Zone 5 — Code facts (OKF v0.2, regenerate-only)
```

## Zone 1 — `_inbox/` (Untriaged)

| Attribute | Value |
| --- | --- |
| **Purpose** | Scratchpad for raw dumps: notes, logs, unclassified fragments, upstream paste |
| **Authority** | None until ingested |
| **Mutability** | Write freely; treat contents as **immutable source material** until MAINTAIN/INGEST moves them |
| **Agent use** | Read as `provided` evidence; never treat as standards |

**When to use:** something arrived that is not yet typed OKF knowledge.  
**When not to use:** durable house rules, playbooks, or modules — those belong in Zones 2–4 after ingest.

After successful ingest, archive or delete the inbox source (see [Maintenance](13-maintenance.md)).

## Zone 2 — `kernel/` (Execution)

The active orchestration layer.

| Subpath | Holds | `type` (if markdown) |
| --- | --- | --- |
| `kernel/*.py` | Tooling (lookup, lint, compile, serve, …) | n/a (not OKF concepts) |
| `kernel/profiles/` | Operational contexts (optional capability templates) | `Profile` |

> Domain knowledge is **not** stored as kernel modules/vendors (`AGENTS.md` §1.1) — it lives under `standards/` and `vault/` and loads via OKF lookup.

**When to use kernel markdown:**

- You need a **Profile** that documents which intents/modes/standards a role uses (schema-only today).

**When not to use:**

- Long encyclopedias of product architecture → `vault/` Concepts/Systems.
- MUST/SHOULD house law → `standards/`.

## Zone 3 — `standards/` (Governance)

Binding technical policies enforced by the **Governance Engine**.

| Attribute | Value |
| --- | --- |
| **Language** | Normative **MUST / SHOULD / FORBIDDEN** |
| **Frontmatter** | `type: Concept` + tag `standard`; Standards also require `owns` and `priority` per [okf-house-schema](../_okf_knowledge/standards/okf-house-schema.md) |
| **Prompt Card** | **Required** — lint fails (`DBG-308`) if missing |

**When to use:** a rule that must constrain every pipeline (simplicity, prompt injection, metadata, domain policy).  
**When not to use:** optional how-tos, one-off runbooks, vendor trigger tables.

Shipped core standards: [Standards](11-standards.md).

## Zone 4 — `vault/` (Knowledge)

Organic, passive memory. Grouped by domain folders; **type is declared in frontmatter**, not only by folder name.

| Subfolder | Typical `type` | Content |
| --- | --- | --- |
| `vault/concepts/` | `Concept` | Evergreen patterns, tool overviews |
| `vault/playbooks/` | `Playbook` | Executable agent procedures |
| `vault/systems/` | `System` | Running systems in the workspace |
| `vault/incidents/` | `Incident` | Post-mortems |
| `vault/references/` | `Reference` | Cached upstream docs |

**When to use:** durable facts agents should find via lookup, without treating them as house law.  
**When not to use:** binding MUST rules (→ standards) or control-plane routing (→ `AGENTS.md`).

## Zone 5 — `code/` (Code facts)

Externally produced OKF v0.2 concepts (`type: Code`) describing the host repo's artifacts — Terraform resources, CloudFormation/Bicep templates, functions, classes, Kubernetes manifests, Ansible plays.

| Attribute | Value |
| --- | --- |
| **Producer** | External generator / CI / manual export — never the agent |
| **Mutability** | **Regenerate-only** — never hand-edited, never ingested via the maintain playbook |
| **Frontmatter** | House fields + v0.2: `schema_version: 0.2`, `language`, `kind`, `source`; optional `depends_on` / `references` / `calls` / `called_by` |
| **Lint** | Missing v0.2 fields → error `DBG-310`; exempt from orphan checks (`DBG-306`) |
| **Lookup** | Indexed like any concept; lowest eviction tier — never crowds curated cards |
| **Evidence** | `observed` — deterministic, but only as fresh as the last regeneration |

**When to use:** the agent needs exact-symbol facts (where is this resource defined, what depends on it) without re-reading source files.  
**When not to use:** curated knowledge of any kind — that belongs in Zones 3–4; `enrich`/`optimize` and §1.6 write-back skip this zone.

## Cross-cutting brain files

| File | Role | Edit when |
| --- | --- | --- |
| `index.md` | Human “map” of the brain | Structure/orientation changes |
| `log.md` | Dated mutation log | **Every** durable brain change |
| `*/index.md` | Progressive disclosure per folder | Add/remove docs in that folder |

## Zone decision flowchart

```
Is it raw / untyped material?
  YES → _inbox/
  NO ↓

Is it a MUST/SHOULD house rule?
  YES → standards/
  NO ↓

Is it a role capability template?
  YES → kernel/profiles/ (Profile)
  NO ↓

Is it a procedure the agent should follow step-by-step?
  YES → vault/playbooks/
  NO ↓

Else → vault/ (Concept, System, Incident, or Reference)
```

## Related

- [Document types](04-document-types.md)
- [Maintenance](13-maintenance.md)
- [`AGENTS.md` §1](../AGENTS.md)
