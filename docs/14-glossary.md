# 14. Glossary

[← Table of contents](README.md)

| Term | Meaning |
| --- | --- |
| **OKF** | Engineering control plane: protocol + brain + kernel tools |
| **AGENTS.md** | Immutable control-plane contract at package root |
| **Brain** | `_okf_knowledge/` — curated OKF knowledge + tools |
| **OKF** | Open Knowledge Format — typed markdown + frontmatter conventions used here |
| **Zone** | One of four brain areas: inbox, kernel, standards, vault |
| **Concept** | Evergreen knowledge document (`type: Concept`) |
| **Standard** | Binding Concept under `standards/` with tag `standard` |
| **Playbook** | Step-by-step executable procedure |
| **System** | Documented running system in the workspace |
| **Incident** | Post-mortem record |
| **Reference** | Cached upstream documentation |
| **Prompt Card** | Slim `## Prompt Card` section injected into generation context |
| **Prompt Pack** | Budgeted set of Prompt Cards for one task (≤ 8 cards; ~1200 token budget) |
| **Pack** | `okf.py pack` — capability line + Prompt Pack in one command (**Rule #1**) |
| **Lookup** | `okf.py lookup` ranked search over frontmatter / `index.json` |
| **Relevance floor** | `--min-score` (default 24); ranked hits below it are dropped, so off-topic queries return an empty pack |
| **Empty pack** | Zero cards — a valid answer meaning the vault has nothing binding on the topic; `pack` still exits 0 |
| **`pack_force_when`** | Frontmatter keyword list that force-includes a card; matched on token boundaries |
| **`resource`** | OKF-reserved frontmatter field: URL or vault-absolute path to the thing a concept describes; printed as the card's `source:` line, never scored |
| **`generated`** | OKF v0.2 frontmatter `{ by, at }` — who produced the content and when; supersedes the v0.1 `timestamp` field |
| **Trust tier** | `unverified` \| `machine-confirmed` \| `human-reviewed`, **derived** from `verified` at read time and never stored; printed as the card's `trust:` line only when it is a caution |
| **Actor convention** | The form an actor takes in `generated.by` / `verified[].by`: `human:<name>`, `process:<name>`, or `<agent>/<model>`. The `human:` prefix is what earns the human-reviewed tier |
| **Provenance (`sources`)** | Optional frontmatter list of upstream entries, each requiring a `resource`; `scrape` writes it with per-claim footnotes instead of a body citation list |
| **Traversal** | Following a card's `related:` / `source:` edge to reach more knowledge, instead of re-running `pack` with a reworded query |
| **Graph** | Untyped `{source, target}` edges in `kernel/src/graph.json`, embedded in `okf-brain.html` by `compile`; lookup hop-boost and the card `related:` footer both read `graph.json` |
| **Index** | `index.json` v2 slim search rows + inverted token map |
| **Capability line** | `caps: READY \| … \| features: …` printed by `pack` / `capabilities` |
| **Runtime state** | `READY` \| `BLOCKED` \| `PENDING_APPROVAL` — only the first two are emitted by the kernel |
| **Path A / B / C** | Generation / Validation / Execution pipelines |
| **Evidence grade** | verified \| observed \| provided \| inferred \| assumed (agent label, not computed) |
| **Exit code** | In reports: 0 success, 1 manual, 2 blocked, 3 missing inputs, 4 unsupported — a convention, not a process exit |
| **Maintain playbook** | Required procedure for all durable brain mutations |
| **Laziness Ladder** | Simplicity First progression from reuse → abstraction-last; the design lens applied after the pack |
| **Bundle-absolute link** | Markdown link like `/vault/...` resolved from `_okf_knowledge/` |

## Related

- [Overview](01-overview.md)
- [Table of contents](README.md)
