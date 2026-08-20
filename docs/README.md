# OKF System Documentation

**Standalone human documentation** for the OKF Engineering Control Plane (`aegis-system`).

This folder explains **what every file is for**, **when to use it**, and **how the protocol routes work**. It is **not** agent prompt fuel — binding agent behavior remains in [`../AGENTS.md`](../AGENTS.md).

| Field | Value |
| --- | --- |
| **Protocol version documented** | `6.0.0` |
| **Kernel version** | `1.9.0` |
| **Package root** | sibling of this `docs/` folder |
| **Brain** | [`../_okf_knowledge/`](../_okf_knowledge/) |

---

## Table of contents

| # | Document | What you learn |
| ---: | --- | --- |
| 1 | [Overview](01-overview.md) | What OKF is / is not; design goal; request + kernel flow diagrams |
| 2 | [Package layout](02-package-layout.md) | Every root-level file and when to open it |
| 3 | [Brain zones](03-brain-zones.md) | The 4-zone map under `_okf_knowledge/` |
| 4 | [Document types](04-document-types.md) | Concept vs Playbook vs System vs Incident vs Reference — **when to use which** |
| 5 | [Frontmatter schema](05-frontmatter-schema.md) | Required YAML fields, `resource`, trust/provenance families, `pack_force_when`, status |
| 6 | [Protocol & routing](06-protocol-routing.md) | Intent matrix, capability line, what the kernel enforces vs what agents follow |
| 7 | [Compiled artifacts](07-compiled-artifacts.md) | `index.json`, `prompt_cards.json`, graph/lint embeds in `okf-brain.html` |
| 8 | [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md) | Cheap retrieval → slim injection (Rule #1 — Pack First); traversal via `related:` edges |
| 9 | [Kernel tools](09-kernel-tools.md) | Every `okf.py` subcommand — purpose and CLI |
| 10 | [Standards (house law)](10-standards.md) | Prompt Injection, Simplicity First, House Schema, Guardrails, Metadata Headers |
| 11 | [Pipelines & output contracts](11-pipelines-and-outputs.md) | Path A / B / C and the report shapes agents follow |
| 12 | [Maintenance & ingest](12-maintenance.md) | How to mutate the brain safely |
| 13 | [Install & day-to-day workflows](13-install-and-workflows.md) | Drop-in install, common commands, visualizer |
| 14 | [Glossary](14-glossary.md) | Terms used across the protocol |
| 15 | [Multi-agent split (future)](15-multi-agent-split.md) | Optional split of `AGENTS.md` into specialized agents |

---

## Quick “which file do I open?”

| You want to… | Open |
| --- | --- |
| Understand binding agent rules | [`../AGENTS.md`](../AGENTS.md) |
| Get a short package intro | [`../README.md`](../README.md) |
| Find *which type* a new doc should be | [Document types](04-document-types.md) |
| Add/change brain knowledge | [Maintenance](12-maintenance.md) + maintain playbook |
| Search the vault | [Lookup](08-lookup-and-prompt-cards.md) |
| Understand `index.json` / compiled embeds | [Compiled artifacts](07-compiled-artifacts.md) |
| Understand optional multi-agent future | [Multi-agent split](15-multi-agent-split.md) |

---

## Relationship to the vault

```
aegis-system/
├── AGENTS.md          ← binding protocol (agents load this)
├── README.md          ← short install blurb
├── docs/              ← THIS FOLDER (standalone human docs)
└── _okf_knowledge/    ← the brain (typed markdown + kernel)
```

`docs/` does **not** replace `_okf_knowledge/`. The vault remains the curated memory agents query. `docs/` is the operator manual for humans (and for onboarding).
