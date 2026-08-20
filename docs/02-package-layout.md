# 2. Package layout

[← Table of contents](README.md)

All paths are relative to the **`aegis-system/`** package directory (the folder that contains `AGENTS.md`).

## Top-level tree

```
aegis-system/
├── AGENTS.md                 # Binding protocol (version in file header)
├── README.md                 # Short install / what’s included
├── BENCH_PROMPT.md           # Optional A/B bench template (OKF vs no-OKF)
├── docs/                     # This documentation (standalone, human)
├── .github/
│   └── workflows/            # CI (e.g. okf-lint)
└── _okf_knowledge/           # The OKF Brain (see 03-brain-zones.md)
```

## Root files — when to use each

| File | Audience | When to use | When **not** to use |
| --- | --- | --- | --- |
| **`AGENTS.md`** | Agents (primary), humans | Binding rules for routing, budgets, Path A/B/C, schema overview — single protocol for all IDEs | Do not paste the whole file into every generation turn; agents load it as the control plane |
| **`README.md`** | Humans installing the package | Zip/drop-in install, quick tool commands | Not the full protocol |
| **`BENCH_PROMPT.md`** | Benchmark / eval runs | A/B tests of OKF-assisted vs bare generation | Day-to-day agent operation |
| **`docs/`** | Humans (and onboarding) | Detailed “what/when/how” manuals | Not a replacement for vault knowledge agents must look up |
| **`.github/workflows/okf-lint.yml`** | CI | Fail PRs when brain lint errors | Locally prefer running `okf.py lint` directly |

## `_okf_knowledge/` at a glance

| Path | Zone | Role |
| --- | --- | --- |
| `_inbox/` | 1 | Raw, untriaged material |
| `kernel/` | 2 | `okf.py` + `src/` tooling |
| `standards/` | 3 | Binding house law |
| `vault/` | 4 | Passive memory (concepts, playbooks, systems, …) |
| `index.md` | — | Human entry map for the brain |
| `log.md` | — | Append-only mutation history |
| `index.json` | compiled | Slim lookup index (v2 + inverted tokens; hop-boost from `graph.json`) |
| `prompt_cards.json` | compiled | Cached Prompt Cards |
| `okf-brain.html` | UI | Interactive brain visualizer; graph + lint payloads are **embedded** here by `compile` / `lint`. Compile also writes `kernel/src/graph.json`, which lookup reads for hop-boost and `pack` for each card's `related:` edges (no `lint.json` sidecar). |

Full zone detail: [Brain zones](03-brain-zones.md).  
Compiled JSON detail: [Compiled artifacts](07-compiled-artifacts.md).

## Package vs project source

OKF is designed to sit **beside** application repos (e.g. under `.cursor/agents/aegis-system/`), not inside `src/`.

| Location | Owns |
| --- | --- |
| Your app repo | Application code, IaC for the product |
| `aegis-system/` | Protocol + curated ops/policy knowledge + tools |

Agents may **generate** artifacts into a target repo during Path A, but durable *OKF memory* stays under `_okf_knowledge/`.

## Versioning note

- Protocol version is declared at the top of `AGENTS.md` (currently `6.0.0`). Treat **`AGENTS.md` as authoritative** for agent behavior.
- Kernel version is declared in the header of `_okf_knowledge/kernel/okf.py` (currently `1.9.0`) and moves independently of the protocol.
- Vault documents carry their own `status` and `generated: { by, at }` provenance in frontmatter; the brain root `index.md` declares the OKF spec version it targets (`okf_version: "0.2"`).

## Related

- [Overview](01-overview.md)
- [Brain zones](03-brain-zones.md)
- [Install & workflows](13-install-and-workflows.md)
