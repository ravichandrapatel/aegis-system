---
okf_version: "0.1"
---

# Aegis brain

Control plane DNA: parent [`AGENTS.md`](/AGENTS.md). Replicate / grow: [Extending Aegis](/vault/concepts/extending-aegis.md).

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
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<keywords>"
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

- [Maintenance](/vault/playbooks/maintain-aegis-system.md) — required for brain mutations
- [Activity log](/log.md)
- Compiled artifacts (`index.json`, `graph.json`) are for tools — not for pasting into prompts
