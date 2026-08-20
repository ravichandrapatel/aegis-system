---
okf_version: "0.2"
---

# OKF brain

Control plane DNA: parent [`AGENTS.md`](/AGENTS.md). Replicate / grow: [Extending OKF](/vault/concepts/extending-okf.md).

## Zones

| Zone | Directory | Purpose |
| --- | --- | --- |
| 1 | [`_inbox/`](/_inbox/) | Untriaged notes |
| 2 | [`kernel/`](/kernel/) | `okf.py` + src |
| 3 | [`standards/`](/standards/) | Binding MUST/SHOULD + Prompt Cards |
| 4 | [`vault/`](/vault/) | Concepts, playbooks, systems, incidents, references |

[Concepts](/vault/concepts/) · [Playbooks](/vault/playbooks/) · [Systems](/vault/systems/) · [Incidents](/vault/incidents/) · [References](/vault/references/)

## Ops

```bash
# from package root (directory with AGENTS.md)
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<keywords>"   # caps line + cards
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
python3 tools/sync_skills.py                                           # after editing a skill
```

- [Maintenance](/vault/playbooks/maintain-okf-system.md) — required for brain mutations
- [Activity log](/log.md)
- Compiled artifacts (`index.json`, `graph.json`) are for tools — not for pasting into prompts
- `pack` reports capabilities inline; an empty pack is a valid answer, not a retry signal
- Cards end with `related:` / `source:` edges — follow one instead of re-packing; when the pack is empty, browse from this page
