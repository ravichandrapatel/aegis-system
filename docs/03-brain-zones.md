# 3. Brain zones

[← Table of contents](README.md)

Aegis maps all brain operations to a **4-zone** tree under `_okf_knowledge/`. Zones encode **lifecycle and authority**: scratch vs law vs execution vs passive memory.

Bundle-absolute links inside the brain (e.g. `/vault/...`, `/standards/...`) are resolved relative to `_okf_knowledge/`.

## Zone map

```
_okf_knowledge/
├── _inbox/          Zone 1 — Untriaged
├── kernel/          Zone 2 — Execution
│   ├── profiles/
│   ├── modules/
│   ├── vendors/
│   └── *.py
├── standards/       Zone 3 — Governance
└── vault/           Zone 4 — Knowledge
    ├── concepts/
    ├── playbooks/
    ├── systems/
    ├── incidents/
    └── references/
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
| `kernel/profiles/` | Operational contexts (roles, allowed modules) | `Profile` |
| `kernel/modules/` | Core domain execution logic & artifact ownership | `Module` |
| `kernel/vendors/` | Cloud/tool-specific execution extensions | `Vendor` |

**When to use kernel markdown:**

- You are defining **how to execute** (triggers, evidence minimums, ownership of generated files).
- You need a **Profile** that gates which modules/vendors/standards load.

**When not to use:**

- Long encyclopedias of product architecture → `vault/` Concepts/Systems.
- MUST/SHOULD house law → `standards/`.

Anti-collision (vendors vs vault) is documented in [Document types](04-document-types.md) and the maintain playbook.

## Zone 3 — `standards/` (Governance)

Binding technical policies enforced by the **Governance Engine**.

| Attribute | Value |
| --- | --- |
| **Language** | Normative **MUST / SHOULD / FORBIDDEN** |
| **Frontmatter** | `type: Concept` + tag `standard`; Standards also require `owns` and `priority` per `AGENTS.md` §1.3 |
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
**When not to use:** binding MUST rules (→ standards) or execution ownership tables (→ modules/vendors).

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

Is it execution routing / ownership / capability?
  YES → kernel/ (Module, Vendor, or Profile)
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
