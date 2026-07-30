# Aegis Vault — The Dictionary

Passive memory lives here under `vault/`. Types are declared in frontmatter; files may be grouped by domain.

## Vault categories

| Category | Directory | Description |
| --- | --- | --- |
| **Concepts** | [`concepts/`](concepts/) | Core definitions and architectural patterns |
| **Playbooks** | [`playbooks/`](playbooks/) | Step-by-step operational procedures |
| **Systems** | [`systems/`](systems/) | Infrastructure and software components |
| **Incidents** | [`incidents/`](incidents/) | Post-mortems and troubleshooting records |
| **References** | [`references/`](references/) | Cached documentation and pin catalogs |

## Operations

* **Starter**: [Extending Aegis](concepts/extending-aegis.md) · [OKF Cognitive Bundle](concepts/okf-cognitive-bundle.md)
* **Ingest**: Drop material in [`_inbox/`](/_inbox/) and follow [Maintain aegis-system](playbooks/maintain-aegis-system.md)
* **Fetch Reference**: `python3 _okf_knowledge/kernel/okf.py scrape "<query or URL>"`
* **Enrich (LLM gaps)**: `python3 _okf_knowledge/kernel/okf.py enrich [--write]`
* **Optimize Cache**: `python3 _okf_knowledge/kernel/okf.py optimize`
* **Compile**: `python3 _okf_knowledge/kernel/okf.py compile`
* **Lint**: `python3 _okf_knowledge/kernel/okf.py lint`
* **Serve**: `python3 _okf_knowledge/kernel/okf.py serve` (local brain + `/api/lint` / `/api/compile`)
