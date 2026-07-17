# Aegis System

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
| `_okf_knowledge/kernel/` | Lookup, Prompt Cards, lint, graph compile, serve |

### Core standards (shipped — do not strip for a “thinner” zip)

| Standard | Why it stays |
| :--- | :--- |
| [`simplicity-first.md`](_okf_knowledge/standards/simplicity-first.md) | Rule #1 — Laziness Ladder |
| [`okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md) | Rule #2 — slim Prompt Cards only; never paste the whole brain |
| [`metadata-headers.md`](_okf_knowledge/standards/metadata-headers.md) | Required file/function metadata for new kernel/code |

`AGENTS.md` Path A binds generation to Rule #2. The kernel tools `okf.py lookup --card` and `okf.py card` exist to enforce that rule — keep the standard next to them. `okf.py lint` fails CI if any `standards/*` concept lacks a `## Prompt Card` (see `.github/workflows/okf-lint.yml`).

### Starter vault docs

| Doc | Role |
| :--- | :--- |
| [`extending-aegis.md`](_okf_knowledge/vault/concepts/extending-aegis.md) | How to grow this empty framework |
| [`maintain-aegis-system.md`](_okf_knowledge/vault/playbooks/maintain-aegis-system.md) | Required procedure for every brain mutation |

Indexes under `systems/`, `references/`, `modules/`, and `vendors/` start empty on purpose.

## Use as an agent or skill

1. Zip this folder (keep `AGENTS.md` and `_okf_knowledge/` together).
2. Unzip and place the **entire directory** into your IDE’s agents or skills folder, for example:
   - Cursor: `.cursor/agents/` or `.cursor/skills/`
   - GitHub Copilot / other: that product’s agents/skills directory
3. Open your project in the IDE and select / invoke the agent that loads this package’s **`AGENTS.md`** (single protocol — no separate DNA file).
4. Ask normally — Aegis follows the protocol and reads/writes knowledge under `_okf_knowledge/`.

Paths are relative to this package folder wherever you drop it.

## Brain tooling (optional)

From this package directory:

```bash
python3 _okf_knowledge/kernel/okf.py lookup "prompt injection"
python3 _okf_knowledge/kernel/okf.py lookup --card --limit 3 "simplicity"
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
python3 _okf_knowledge/kernel/okf.py serve
```

Then open `http://localhost:8080/aegis-brain.html`.

## Add knowledge

1. Drop raw notes in `_okf_knowledge/_inbox/`.
2. Ask Aegis to **MAINTAIN / INGEST**, or follow [`maintain-aegis-system.md`](_okf_knowledge/vault/playbooks/maintain-aegis-system.md) yourself.
3. Recompile and lint from this package directory:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

See [`extending-aegis.md`](_okf_knowledge/vault/concepts/extending-aegis.md) for where Concepts, Playbooks, Systems, and References go.
