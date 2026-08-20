# OKF System

Portable Engineering Control Plane: `AGENTS.md` (protocol) + `_okf_knowledge/` (brain).

This is a **clean-slate** package: domain-agnostic control plane only. No product modules, systems, or trained domain vaults ship here — you add those after install.

**Human documentation (standalone):** [`docs/`](docs/README.md) — detailed TOC covering every file, when to use what, protocol, tools, and workflows.

**OKF vs no-OKF A/B bench (parent prompt template):** [`BENCH_PROMPT.md`](BENCH_PROMPT.md) — fill placeholders, paste into chat, launch two subagents, plot metrics.

## What’s included

| Piece | Role |
| :--- | :--- |
| [`AGENTS.md`](AGENTS.md) | Immutable protocol (routing, Path A/B/C, lookup rules) |
| `_okf_knowledge/standards/` | Binding house law (keep these) |
| `_okf_knowledge/vault/` | Empty slots + starter docs |
| `_okf_knowledge/kernel/okf.py` + `okf/` | Lookup, Prompt Cards, lint, graph compile, serve |

### IDE bindings (shipped)

| Surface | Path |
| --- | --- |
| Cursor rule | `.cursor/rules/okf.mdc` |
| Cursor skills / commands | `.cursor/skills/*/SKILL.md`, `.cursor/commands/*.md` |
| Copilot instructions | `.github/copilot-instructions.md`, `.github/instructions/` |
| Copilot agent / skills / prompts | `.github/agents/`, `.github/skills/`, `.github/prompts/` |

Skills/prompts: `okf-discover`, `okf-pack`, `grill-me`, `mutation-gate`, `okf-writeback`, `okf-maintain`, `okf-review`, `code-review`.

### Core standards (shipped — do not strip for a “thinner” zip)

| Standard | Why it stays |
| :--- | :--- |
| [`okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md) | Rule #1 — Pack First: slim Prompt Cards only; never paste the whole brain |
| [`okf-house-schema.md`](_okf_knowledge/standards/okf-house-schema.md) | Frontmatter + Prompt Card rules that `okf.py lint` checks |
| [`ide-context-guardrails.md`](_okf_knowledge/standards/ide-context-guardrails.md) | No `@workspace` dumps; pack-first cards; `rg` over legacy search |
| [`simplicity-first.md`](_okf_knowledge/standards/simplicity-first.md) | Laziness Ladder — the design lens applied after the pack |
| [`metadata-headers.md`](_okf_knowledge/standards/metadata-headers.md) | Required file/function metadata for new runtime code |

`AGENTS.md` binds non-trivial work to Rule #1 (Pack First). The runtime tools `okf.py pack`, `okf.py lookup --card`, and `okf.py card` exist to make that rule cheap — keep the standard next to them. `okf.py lint` fails CI if any `standards/*` concept lacks a `## Prompt Card` (see `.github/workflows/okf-lint.yml`).

### Starter vault docs

| Doc | Role |
| :--- | :--- |
| [`extending-okf.md`](_okf_knowledge/vault/concepts/extending-okf.md) | How to grow this empty framework |
| [`maintain-okf-system.md`](_okf_knowledge/vault/playbooks/maintain-okf-system.md) | Required procedure for every brain mutation |

Indexes under `systems/`, `references/`, and `incidents/` start empty on purpose.

## Use as an agent or skill

1. Zip this folder (keep `AGENTS.md` and `_okf_knowledge/` together).
2. Unzip and place the **entire directory** into your IDE’s agents or skills folder, for example:
   - Cursor: `.cursor/agents/` or `.cursor/skills/`
   - GitHub Copilot / other: that product’s agents/skills directory
3. Open your project in the IDE and select / invoke the agent that loads this package’s **`AGENTS.md`** (single protocol — no separate DNA file).
4. Ask normally — OKF follows the protocol and reads/writes knowledge under `_okf_knowledge/`.

Paths are relative to this package folder wherever you drop it.

## Brain tooling (optional)

From this package directory:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "prompt injection"
python3 _okf_knowledge/kernel/okf.py lookup "prompt injection"
python3 _okf_knowledge/kernel/okf.py lookup --card --limit 3 "simplicity"
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
python3 _okf_knowledge/kernel/okf.py serve
```

`pack` is the one command agents run first: it prints a `caps: READY|BLOCKED …` line and then the Prompt Cards. It always exits `0` — zero cards means the vault has nothing binding on that topic.

Then open `http://localhost:8080/okf-brain.html`.

## Add knowledge

1. Drop raw notes in `_okf_knowledge/_inbox/`.
2. Ask OKF to **MAINTAIN / INGEST**, or follow [`maintain-okf-system.md`](_okf_knowledge/vault/playbooks/maintain-okf-system.md) yourself.
3. Recompile and lint from this package directory:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

See [`extending-okf.md`](_okf_knowledge/vault/concepts/extending-okf.md) for where Concepts, Playbooks, Systems, and References go.
