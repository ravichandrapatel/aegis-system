---
type: Playbook
title: Maintain aegis-system
description: How to add or update concepts, playbooks, references, scripts, and skills in the aegis-system OKF vault — with post-change verification.
tags: [aegis-system, ingest, maintenance, okf, procedure]
timestamp: 2026-07-13T14:50:00Z
status: active
---

# Trigger

You need to add or change durable knowledge in aegis-system: a concept, house standard,
playbook, reference, vault script, agent bridge, or Cursor skill.

# Preconditions

- [AGENTS.md](/AGENTS.md) §1.2 binds all brain mutations to this playbook — follow it end-to-end.
- Read [AGENTS.md](/AGENTS.md) §1.3 for the OKF frontmatter schema before creating files.
- Raw source material (if any) is in [`_inbox/`](/_inbox/) and has not been edited.
- You know which `type` the content is (see decision table below).

# What to create — decision table

| You are documenting… | `type` | Directory | Also update |
|----------------------|--------|-----------|-------------|
| Evergreen knowledge, pattern, tool overview | `Concept` | `vault/` (by domain) | `vault/index.md` |
| House rule (MUST/SHOULD) | `Concept` + tag `standard` | `standards/` | [standards/index.md](/standards/index.md) |
| Executable agent procedure | `Playbook` | `vault/playbooks/` | [playbooks/index.md](/vault/playbooks/index.md) |
| Cached upstream docs | `Reference` | `vault/references/` | Run `kernel/cache_optimizer.py` |
| Running system in workspace | `System` | `vault/systems/` | [systems/index.md](/vault/systems/index.md) |
| Post-mortem | `Incident` | `vault/incidents/` | Link to affected systems/playbooks |
| Core execution logic / ownership | `Module` | `kernel/modules/` | [modules/index.md](/kernel/modules/index.md) |
| Cloud/tool execution extension | `Vendor` | `kernel/vendors/` | [vendors/index.md](/kernel/vendors/index.md) |
| Vault tooling (lint, compile, scrape) | Python script | `kernel/` | This playbook § Scripts |
| Control-plane schema / persona | Markdown | `AGENTS.md` (package root, next to `_okf_knowledge/`) | [_okf_knowledge/index.md](/index.md) |

## Anti-collision rule (vendors vs vault)

| Layer | Owns | MUST NOT |
|-------|------|----------|
| `kernel/vendors/` (`type: Vendor`) | Triggers, minimum evidence, execution pipelines, artifact ownership vs modules | Duplicate System/Concept encyclopedias of the product |
| `vault/` (`Concept` / `System` / `Playbook` / …) | Passive facts, architecture, runbooks, incidents, cached docs | Embed vendor routing/trigger tables |

Cross-link instead: Vendor → System/Concept; System → Vendor. Precedence on conflict: vendors beat vault ([AGENTS.md](/AGENTS.md) §2.2).


# Add or update a concept

## 1. Choose path and filename

- One concept per file; kebab-case filename matching the topic.
- House standards go in `standards/` with `tags: [standard, …]`.
- Domain concepts go in `vault/`.

## 2. Frontmatter (required)

```yaml
---
type: Concept
title: Human-readable name
description: One-line summary for indexes and okf_lookup.
tags: [kebab-case, topic]
timestamp: 2026-07-13T00:00:00Z
status: active
---
```

## 3. Body

- Prefer headings, tables, lists, and fenced code over long prose.
- Standards: normative **MUST** / **SHOULD** / **FORBIDDEN** language.
- Binding standards **MUST** include a non-empty `## Prompt Card` section (≤150 tokens / ~600 chars) — enforced by `okf_lint.py` (`DBG-308` / `DBG-309`). See [OKF Prompt Injection](/standards/okf-prompt-injection.md).
- Other agent-facing concepts **SHOULD** include a `## Prompt Card` for slim injection.
- External claims: `# Citations` with numbered `[1] [title](url)` entries.
- Link to related concepts with bundle-absolute paths.

## 4. Cross-links (both directions)

- New concept MUST link to at least one existing related concept.
- Update those existing files to link back.
- Update every affected `index.md` on the path from root to the file.

# Add or update a playbook

## Required sections

```markdown
# Trigger
# Preconditions
# Steps
# Verification
```

- Add a one-line entry to [playbooks/index.md](/vault/playbooks/index.md).

# Add or update a script

Scripts live in `kernel/`; they are **not** OKF concepts.

| Script | Role |
|--------|------|
| `graph_compiler.py` | Regenerate `graph.json`, `index.json`, `prompt_cards.json`; embed graph in `aegis-brain.html` |
| `okf_lint.py` | Conformance + broken links + orphans + **standards Prompt Card gate** → `lint.json` |
| `prompt_card.py` | Extract `## Prompt Card` sections for slim agent injection |
| `okf_lookup.py` | Search via `index.json` (fallback: live vault); list hits or budgeted `--card` |
| `registry_scraper.py` | JIT upstream fetch → `vault/` |
| `cache_optimizer.py` | Normalize references, rebuild vault indexes, run compiler |
| `serve_vault.py` | Local server + `POST /api/lint` |
| `okf_common.py` | Shared vault helpers |

# Post-change checklist

Run after **every** concept or playbook add/update:

```bash
# From this package directory (wherever it was dropped in agents/)
python3 _okf_knowledge/kernel/graph_compiler.py
python3 _okf_knowledge/kernel/okf_lint.py
```

| Step | Action |
|------|--------|
| 1 | Update affected `index.md` files |
| 2 | Cross-link both directions |
| 3 | Append entry to [log.md](/log.md) |
| 4 | Run `graph_compiler.py` |
| 5 | Run `okf_lint.py` — must end with `0 error(s)` |
| 6 | Archive or delete `_inbox/` source after ingest |

# Verification

- [ ] New/edited file has valid frontmatter per [AGENTS.md](/AGENTS.md) §1.3
- [ ] Every affected `index.md` lists the new or changed page
- [ ] `python3 _okf_knowledge/kernel/okf_lint.py` reports clean (or warnings only, with plan)
- [ ] `log.md` has a dated entry
- [ ] Change followed this playbook as required by [AGENTS.md](/AGENTS.md) §1.2

# Related

- Schema contract + maintenance binding: [AGENTS.md](/AGENTS.md) (§1.2, §1.3, MAINTAIN/INGEST intent)
- Standards: [Simplicity First](/standards/simplicity-first.md)
- Modules: [kernel/modules/](/kernel/modules/index.md)
- Vendors: [kernel/vendors/](/kernel/vendors/index.md)
- Starter: [Extending Aegis](/vault/concepts/extending-aegis.md)
