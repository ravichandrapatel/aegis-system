# 3. Brain zones

[← Table of contents](README.md)

Aegis maps all brain operations to a **4-zone** tree under `_okf_knowledge/`. Zones encode **lifecycle and authority**: scratch vs execution vs law vs passive memory.

Bundle-absolute links inside the brain (e.g. `/vault/...`, `/standards/...`) are resolved relative to `_okf_knowledge/`.

## Zone map

```
_okf_knowledge/
├── _inbox/          Zone 1 — Untriaged
├── kernel/          Zone 2 — Execution (`okf.py` + `src/`)
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
**When not to use:** durable house rules or playbooks — those belong in Zones 3–4 after ingest.

## Zone 2 — `kernel/` (Execution)

The active orchestration layer: `okf.py` CLI and `kernel/src/` (pack, lookup, compile, lint, scrape, serve, …).

Kernel markdown role templates (`profiles/`) and machine Zone-5 `code/` facts were removed from this portable package — domain knowledge loads via OKF lookup under `standards/` and `vault/` only.

## Zone 3 — `standards/` (Governance)

Binding technical policies (`type: Concept` + tag `standard`). Prompt Card required — lint fails (`DBG-308`) if missing.

Shipped core standards: [Standards](11-standards.md).

## Zone 4 — `vault/` (Knowledge)

| Subfolder | Typical `type` | Content |
| --- | --- | --- |
| `vault/concepts/` | `Concept` | Evergreen patterns |
| `vault/playbooks/` | `Playbook` | Executable procedures |
| `vault/systems/` | `System` | Running systems |
| `vault/incidents/` | `Incident` | Post-mortems |
| `vault/references/` | `Reference` | Cached upstream docs |

## Cross-cutting brain files

| File | Role |
| --- | --- |
| `index.md` | Human map of the brain |
| `log.md` | Dated mutation log |
| `*/index.md` | Progressive disclosure per folder |

## Zone decision flowchart

```
Is it raw / untyped material?
  YES → _inbox/
  NO ↓

Is it a MUST/SHOULD house rule?
  YES → standards/
  NO ↓

Is it a procedure the agent should follow step-by-step?
  YES → vault/playbooks/
  NO ↓

Else → vault/ (Concept, System, Incident, or Reference)
```

## Related

- [Document types](04-document-types.md)
- [Maintenance](13-maintenance.md)
- [Package layout](02-package-layout.md)
