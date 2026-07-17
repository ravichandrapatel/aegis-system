---
okf_version: "0.1"
---

# 🛡️ Aegis Engineering Control Plane

Welcome to the **Aegis Brain**. 5 zones per [AGENTS.md](/AGENTS.md). Starter: [Extending Aegis](/vault/concepts/extending-aegis.md).

**Package:** `AGENTS.md` (bootloader) + `_okf_knowledge/` (this directory). Zip the parent folder and drop it into your IDE **agents** folder.

## 🧠 The 5-Zone Brain Map

| Zone | Directory | Purpose | Analogy |
| :--- | :--- | :--- | :--- |
| **Zone 1** | [`_inbox/`](/_inbox/) | Untriaged material, logs, and raw queries. | The Scratchpad |
| **Zone 2** | [`kernel/`](/kernel/) | Orchestration scripts (`okf.py`); optional profiles. | The CPU |
| **Zone 3** | [`standards/`](/standards/) | Binding technical policies and MUST/SHOULD rules. | The Law |
| **Zone 4** | [`vault/`](/vault/) | Passive memory: Concepts, Playbooks, Systems, etc. | The Dictionary |
| **Zone 5** | [`code/`](/code/) | OKF v0.2 code facts (`type: Code`) — regenerate-only. | The Code Map |

> [Concepts](/vault/concepts/) | [Playbooks](/vault/playbooks/) | [Systems](/vault/systems/) | [Incidents](/vault/incidents/) | [References](/vault/references/)

## 📊 Compiled artifacts (not for LLM paste)

* [**Lookup Index**](/index.json) — Frontmatter index + inverted tokens + hop adjacency for `okf.py lookup`.
* [**Prompt Cards**](/prompt_cards.json) — Compile-time `## Prompt Card` cache.
* **Agent routing:** `python3 _okf_knowledge/kernel/okf.py lookup --card "<query>"` — never dump the index into prompts.

## 🖥 Visualizer

* [**aegis-brain.html**](/aegis-brain.html) — Interactive graph (graph + lint payloads embedded in the HTML; no sidecar JSON).
* Serve: `python3 _okf_knowledge/kernel/okf.py serve`

## 🚀 Active Protocol

* [**AGENTS.md**](/AGENTS.md) — Bootloader control plane (routing, invariants, output contracts).
* [**OKF House Schema**](/standards/okf-house-schema.md) — Document types + frontmatter (lint-enforced).
* [**Maintenance**](/vault/playbooks/maintain-aegis-system.md) — Required for all brain mutations.
* [**Activity Log**](/log.md) — Historical record of system mutations.
