# 15. Glossary

[← Table of contents](README.md)

| Term | Meaning |
| --- | --- |
| **Aegis** | Engineering control plane: protocol + brain + kernel tools |
| **AGENTS.md** | Immutable control-plane contract at package root |
| **Brain** | `_okf_knowledge/` — curated OKF knowledge + tools |
| **OKF** | Open Knowledge Format — typed markdown + frontmatter conventions used here |
| **Zone** | One of four brain areas: inbox, kernel, standards, vault |
| **Concept** | Evergreen knowledge document (`type: Concept`) |
| **Standard** | Binding Concept under `standards/` with tag `standard` |
| **Playbook** | Step-by-step executable procedure |
| **Module** / **Vendor** | Retired concepts — no kernel registries exist (`AGENTS.md` §4.1); domain knowledge loads via lookup over `standards/` + `vault/` |
| **Profile** | Dynamic operational context (`type: Profile`) under `kernel/profiles/`; schema in `_schema.md` |
| **Dynamic Profile** | Role-specific Profile instantiated from `_schema.md` (intents, modes, modules, standards) |
| **System** | Documented running system in the workspace |
| **Incident** | Post-mortem record |
| **Reference** | Cached upstream documentation |
| **Prompt Card** | Slim `## Prompt Card` section injected into generation context |
| **Prompt Pack** | Budgeted set of Prompt Cards for one turn (≤ 8 cards hard; target ≈1200 tokens) |
| **Lookup** | `okf.py lookup` ranked search over frontmatter / `index.json` |
| **Graph** | Nodes/edges embedded in `aegis-brain.html` by `compile` (no `graph.json` sidecar); lookup adjacency lives in `index.json` |
| **Index** | `index.json` slim search rows |
| **Governance Engine** | Enforcement of standards / owns / priority during pipelines |
| **Capability Check** | Profile allow-list verification before work (fail → exit 4) |
| **Path A / B / C** | Generation / Validation / Execution pipelines |
| **Evidence grade** | verified \| observed \| provided \| inferred \| assumed |
| **Exit code** | 0 success, 1 manual, 2 blocked, 3 missing inputs, 4 unsupported |
| **Maintain playbook** | Required procedure for all durable brain mutations |
| **Laziness Ladder** | Rule #1 progression from reuse → abstraction-last |
| **Bundle-absolute link** | Markdown link like `/vault/...` resolved from `_okf_knowledge/` |

## Related

- [Overview](01-overview.md)
- [Table of contents](README.md)
