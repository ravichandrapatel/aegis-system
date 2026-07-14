# 2. Package layout

[← Table of contents](README.md)

All paths are relative to the **`aegis-system/`** package directory (the folder that contains `AGENTS.md`).

## Top-level tree

```
aegis-system/
├── AGENTS.md                 # Binding protocol (v4.6.x)
├── ADR.md                    # Architecture Decision Record
├── README.md                 # Short install / what’s included
├── BENCH_PROMPT.md           # Optional A/B bench template (OKF vs no-OKF)
├── docs/                     # This documentation (standalone, human)
├── .github/
│   ├── agents/aegis.agent.md # GitHub Copilot agent profile (derived from AGENTS.md)
│   └── workflows/            # CI (e.g. okf-lint)
└── _okf_knowledge/           # The Aegis Brain (see 03-brain-zones.md)
```

## Root files — when to use each

| File | Audience | When to use | When **not** to use |
| --- | --- | --- | --- |
| **`AGENTS.md`** | Agents (primary), humans | Binding rules for routing, budgets, Path A/B/C, schema overview | Do not paste the whole file into every generation turn; agents load it as the control plane |
| **`ADR.md`** | Humans, architects | Understand *why* decisions exist (D1–Dn) | Not agent prompt fuel; not a substitute for standards |
| **`README.md`** | Humans installing the package | Zip/drop-in install, quick tool commands | Not the full protocol |
| **`BENCH_PROMPT.md`** | Benchmark / eval runs | A/B tests of OKF-assisted vs bare generation | Day-to-day agent operation |
| **`docs/`** | Humans (and onboarding) | Detailed “what/when/how” manuals | Not a replacement for vault knowledge agents must look up |
| **`.github/agents/aegis.agent.md`** | GitHub Copilot | Agent profile with YAML frontmatter; copy to target repo `.github/agents/` on install | Not used by Cursor (use `AGENTS.md` directly) |
| **`.github/workflows/okf-lint.yml`** | CI | Fail PRs when brain lint errors | Locally prefer running `okf.py lint` directly |

## `_okf_knowledge/` at a glance

| Path | Zone | Role |
| --- | --- | --- |
| `_inbox/` | 1 | Raw, untriaged material |
| `kernel/` | 2 | Scripts + profiles + modules + vendors |
| `standards/` | 3 | Binding house law |
| `vault/` | 4 | Passive memory (concepts, playbooks, systems, …) |
| `index.md` | — | Human entry map for the brain |
| `log.md` | — | Append-only mutation history |
| `graph.json` | compiled | Visualizer + traversal artifact |
| `index.json` | compiled | Slim lookup index |
| `prompt_cards.json` | compiled | Cached Prompt Cards |
| `lint.json` | compiled | Last lint report for UI |
| `aegis-brain.html` | UI | Interactive brain visualizer |

Full zone detail: [Brain zones](03-brain-zones.md).  
Compiled JSON detail: [Compiled artifacts](08-compiled-artifacts.md).

## Package vs project source

Aegis is designed to sit **beside** application repos (e.g. under `.cursor/agents/aegis-system/`), not inside `src/`.

| Location | Owns |
| --- | --- |
| Your app repo | Application code, IaC for the product |
| `aegis-system/` | Protocol + curated ops/policy knowledge + tools |

Agents may **generate** artifacts into a target repo during Path A, but durable *Aegis memory* stays under `_okf_knowledge/`.

## Versioning note

- Protocol version is declared at the top of `AGENTS.md` (e.g. `4.6.1`).
- ADR may lag slightly on the printed protocol version in its header table; treat **`AGENTS.md` as authoritative** for agent behavior.
- Vault documents carry their own `status` / timestamps in frontmatter.

## Related

- [Overview](01-overview.md)
- [Brain zones](03-brain-zones.md)
- [Install & workflows](14-install-and-workflows.md)
