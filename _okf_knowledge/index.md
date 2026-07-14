---
okf_version: "0.1"
---

# 🛡️ Aegis Engineering Control Plane

Welcome to the **Aegis Brain**. 4 zones per [AGENTS.md](/AGENTS.md). Starter: [Extending Aegis](/vault/concepts/extending-aegis.md).

**Package:** `AGENTS.md` + `_okf_knowledge/` (this directory). Zip the parent folder and drop it into your IDE **agents** folder.

## 🧠 The 4-Zone Brain Map

| Zone | Directory | Purpose | Analogy |
| :--- | :--- | :--- | :--- |
| **Zone 1** | [`_inbox/`](/_inbox/) | Untriaged material, logs, and raw queries. | The Scratchpad |
| **Zone 2** | [`kernel/`](/kernel/) | Orchestration scripts, modules, and vendors. | The CPU |
| **Zone 3** | [`standards/`](/standards/) | Binding technical policies and MUST/SHOULD rules. | The Law |
| **Zone 4** | [`vault/`](/vault/) | Passive memory: Concepts, Playbooks, Systems, etc. | The Dictionary |

> [Concepts](/vault/concepts/) | [Playbooks](/vault/playbooks/) | [Systems](/vault/systems/) | [Incidents](/vault/incidents/) | [References](/vault/references/)

## 📊 System Telemetry & Context

* [**System Graph**](/graph.json) — Nodes and edges for the brain visualizer (not for LLM paste).
* [**Lookup Index**](/index.json) — Slim frontmatter index for `okf_lookup` (compiled; not for LLM paste).
* [**Health Report**](/lint.json) — Structured lint report for the visualizer.
* **Agent routing:** `python3 _okf_knowledge/kernel/okf.py lookup "<query>"` then `--card` — never dump the graph into prompts.

## 🚀 Active Protocol

* [**AGENTS.md**](/AGENTS.md) — Control plane (v4.3.0).
* [**Modules**](/kernel/modules/) — Core domain execution logic.
* [**Vendors**](/kernel/vendors/) — Cloud/tool-specific extensions.
* [**Maintenance**](/vault/playbooks/maintain-aegis-system.md) — Required for all brain mutations.
* [**Activity Log**](/log.md) — Historical record of system mutations.

---

*Open [aegis-brain.html](/aegis-brain.html) for the interactive visualizer.*
