# Aegis System Documentation

**Standalone human documentation** for the Aegis Engineering Control Plane (`aegis-system`).

This folder explains **what every file is for**, **when to use it**, and **how the protocol routes work**. It is **not** agent prompt fuel — binding agent behavior remains in [`../AGENTS.md`](../AGENTS.md). Architecture rationale lives in [`../ADR.md`](../ADR.md).

| Field | Value |
| --- | --- |
| **Protocol version documented** | `4.6.1` |
| **Package root** | sibling of this `docs/` folder |
| **Brain** | [`../_okf_knowledge/`](../_okf_knowledge/) |

---

## Table of contents

| # | Document | What you learn |
| ---: | --- | --- |
| 1 | [Overview](01-overview.md) | What Aegis is / is not; design goal; how pieces fit |
| 2 | [Package layout](02-package-layout.md) | Every root-level file and when to open it |
| 3 | [Brain zones](03-brain-zones.md) | The 4-zone map under `_okf_knowledge/` |
| 4 | [Document types](04-document-types.md) | Concept vs Playbook vs Module vs Vendor vs Profile — **when to use which** |
| 5 | [Frontmatter schema](05-frontmatter-schema.md) | Required YAML fields, `owns`, `priority`, status |
| 6 | [Protocol & routing](06-protocol-routing.md) | Intent matrix, pre-flight state machine, knowledge precedence |
| 7 | [Profiles](07-profiles.md) | Dynamic Profiles (`_schema.md`), RBAC capabilities, Capability Check |
| 8 | [Compiled artifacts](08-compiled-artifacts.md) | `graph.json`, `index.json`, `prompt_cards.json`, `lint.json` |
| 9 | [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md) | Cheap retrieval → slim injection (Rule #2) |
| 10 | [Kernel tools](10-kernel-tools.md) | Every `kernel/*.py` script — purpose and CLI |
| 11 | [Standards (house law)](11-standards.md) | Simplicity First, Prompt Injection, Metadata Headers |
| 12 | [Pipelines & output contracts](12-pipelines-and-outputs.md) | Path A / B / C and required report shapes |
| 13 | [Maintenance & ingest](13-maintenance.md) | How to mutate the brain safely |
| 14 | [Install & day-to-day workflows](14-install-and-workflows.md) | Drop-in install, common commands, visualizer |
| 15 | [Glossary](15-glossary.md) | Terms used across the protocol |
| 16 | [Multi-agent split (future)](16-multi-agent-split.md) | Optional split of `AGENTS.md` into specialized agents (ADR D10) |

---

## Quick “which file do I open?”

| You want to… | Open |
| --- | --- |
| Understand binding agent rules | [`../AGENTS.md`](../AGENTS.md) |
| Understand *why* the architecture exists | [`../ADR.md`](../ADR.md) |
| Get a short package intro | [`../README.md`](../README.md) |
| Find *which type* a new doc should be | [Document types](04-document-types.md) |
| Add/change brain knowledge | [Maintenance](13-maintenance.md) + maintain playbook |
| Search the vault | [Lookup](09-lookup-and-prompt-cards.md) |
| Understand `graph.json` / `index.json` | [Compiled artifacts](08-compiled-artifacts.md) |
| Understand optional multi-agent future | [Multi-agent split](16-multi-agent-split.md) + [`ADR.md` D10](../ADR.md) |

---

## Relationship to the vault

```
aegis-system/
├── AGENTS.md          ← binding protocol (agents load this)
├── ADR.md             ← architecture decisions (humans)
├── README.md          ← short install blurb
├── docs/              ← THIS FOLDER (standalone human docs)
└── _okf_knowledge/    ← the brain (typed markdown + kernel)
```

`docs/` does **not** replace `_okf_knowledge/`. The vault remains the curated memory agents query. `docs/` is the operator manual for humans (and for onboarding).
