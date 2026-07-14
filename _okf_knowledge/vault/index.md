# Aegis Vault — The Dictionary

Passive memory lives here under `vault/`. Types are declared in frontmatter; files may be grouped by domain.

**Boundary:** `kernel/vendors/` and `kernel/modules/` are Zone 2 execution (`type: Vendor` / `type: Module`). Do not put encyclopedic product docs there — put those here as `System` / `Concept` and cross-link.

## 📂 Vault Categories

| Category | Directory | Description |
| :--- | :--- | :--- |
| **Concepts** | [`concepts/`](concepts/) | Core definitions and architectural patterns. |
| **Playbooks** | [`playbooks/`](playbooks/) | Step-by-step operational procedures. |
| **Systems** | [`systems/`](systems/) | Infrastructure and software component definitions. |
| **Incidents** | [`incidents/`](incidents/) | Post-mortems and troubleshooting records. |
| **References** | [`references/`](references/) | Cached documentation and third-party specs. |

## 🛠️ Operations

* **Starter**: [Extending Aegis](concepts/extending-aegis.md) — how to grow this framework.
* **Ingest material**: Drop it in [`_inbox/`](/_inbox/) and follow [Maintain aegis-system](playbooks/maintain-aegis-system.md).
* **Fetch Reference**: `python3 _okf_knowledge/kernel/okf.py scrape "<topic>"` *(from package root)*
* **Optimize Cache**: `python3 _okf_knowledge/kernel/okf.py optimize`
* **Compile Graph**: `python3 _okf_knowledge/kernel/okf.py compile`
* **Lint Vault**: `python3 _okf_knowledge/kernel/okf.py lint`
