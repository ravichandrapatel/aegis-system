---
type: System
title: OKF Runtime CLI
description: Runnable okf.py surface this package ships — pack, compile, lint, scrape, serve, tokens.
tags: [okf, runtime, cli, pack, compile]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: [okf.py, runtime cli, compile lint, scrape serve]
---

# OKF Runtime CLI

This repository's product surface is `_okf_knowledge/kernel/okf.py` (thin shim). Implementation is the installable package `_okf_knowledge/kernel/okf/` (`python3 -m okf` from `kernel/`). Lookup caches (`index.json`, `prompt_cards.json`) live at the brain root `_okf_knowledge/`; `graph.json` lives only under `kernel/okf/assets/` (with `brain.html`). Agents and humans run commands from the package root (the directory that contains `AGENTS.md`).

## Commands that matter

| Command | Role |
| --- | --- |
| `pack` | Caps line + budgeted Prompt Cards (Rule #1). Prefer this over `lookup --card`. |
| `compile` | Rebuilds brain-root `index.json` / `prompt_cards.json` and `okf/assets/graph.json`; embeds graph into `okf/assets/brain.html`. |
| `lint` | Schema + link + trust-shape checks. Zero errors required before Rung 2 ingest. |
| `scrape` | Fetch upstream docs into `vault/references/` with `resource` + `sources` frontmatter. |
| `serve` | Read-only loopback visualizer — no mutate APIs, no auth. |
| `tokens` | Count tokens for paths (tiktoken if installed, else heuristic). |
| `capabilities` | Verbose probe; normally unnecessary because `pack` prints `caps:`. |

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<keywords>"
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

## Layout

```text
_okf_knowledge/
  kernel/
    okf.py                        # CLI shim
    pyproject.toml
    okf/                          # importable package
      assets/
        brain.html                # visualizer template
        graph.json                # hop-boost + serve /graph.json
  index.json, prompt_cards.json
  standards/ vault/ _inbox/ …
```

## Hard rules for this package

- After editing `.cursor/skills/`, run `python3 tools/sync_skills.py` — `.github/skills/` is generated.
- Brain mutations follow [Maintain OKF System](/vault/playbooks/maintain-okf-system.md).
- Nested frontmatter needs PyYAML (`nested_yaml` on the caps line). Without it, nested docs fail parse loudly.

## Prompt Card

```text
Package: `_okf_knowledge/kernel/okf.py` → `kernel/okf/` package.
index.json + prompt_cards.json at brain root; graph.json only under okf/assets/.
pack = caps + cards (Rule #1). compile then lint after brain edits. serve is read-only loopback.
scrape writes resource+sources. Sync skills: python3 tools/sync_skills.py after .cursor/skills edits.
```

# Related

- Bundle shape: [OKF Cognitive Bundle](/vault/concepts/okf-cognitive-bundle.md)
- Replication: [Extending OKF](/vault/concepts/extending-okf.md)
- Maintenance: [Maintain OKF System](/vault/playbooks/maintain-okf-system.md)
- Caps: [OKF Capability Discovery](/vault/concepts/okf-capability-discovery.md)
