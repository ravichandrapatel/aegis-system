# 14. Install & day-to-day workflows

[← Table of contents](README.md)

## Install (drop-in agent package)

1. Keep `AGENTS.md` and `_okf_knowledge/` together (zip the `aegis-system` folder).  
2. Place the **entire directory** into your IDE agents/skills location, for example:
   - Cursor: `.cursor/agents/` or `.cursor/skills/`
   - GitHub Copilot: `.github/agents/`
3. Select / invoke **Aegis** (this package’s `AGENTS.md`).  
4. Ask normally — Aegis follows the protocol and reads/writes under `_okf_knowledge/`.

Paths in the protocol are **relative to the package directory** wherever you dropped it.

## Daily workflows

### A. “I need the right rule / playbook”

```bash
cd /path/to/aegis-system
python3 _okf_knowledge/kernel/okf.py lookup "your topic"
python3 _okf_knowledge/kernel/okf.py lookup --card "your topic"
```

See [Lookup](09-lookup-and-prompt-cards.md).

### B. “I changed brain markdown”

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

See [Maintenance](13-maintenance.md).

### C. “I want to see the graph”

```bash
python3 _okf_knowledge/kernel/okf.py serve
# http://localhost:8080/aegis-brain.html
```

### D. “Raw notes just landed”

1. Put them in `_okf_knowledge/_inbox/`  
2. Ask Aegis to **MAINTAIN / INGEST**, or follow the maintain playbook yourself  
3. Compile + lint + log  

### E. “CI should guard the brain”

Workflow: `.github/workflows/okf-lint.yml` runs `okf.py lint`. Keep Prompt Cards on all standards.

## What not to commit casually

| Artifact | Guidance |
| --- | --- |
| Source markdown under vault/standards/kernel | **Do** commit — source of truth |
| `graph.json` / `index.json` / `prompt_cards.json` | Often committed for offline UI; always regenerable |
| `lint.json` | Regenerable; useful for UI |
| `__pycache__/` | Ignored |

## Bench / evaluation

Optional template: [`../BENCH_PROMPT.md`](../BENCH_PROMPT.md) for OKF vs no-OKF A/B runs.

## Human docs vs agent brain

| Tree | Role |
| --- | --- |
| `docs/` | Standalone human manuals (this set) |
| `_okf_knowledge/` | Curated memory agents **must** look up |
| `AGENTS.md` | Binding protocol agents load |

Keep them consistent when protocol changes: update `AGENTS.md` first, then refresh relevant `docs/*.md` pages.

## Related

- [Package layout](02-package-layout.md)
- [Kernel tools](10-kernel-tools.md)
- [`../README.md`](../README.md)
