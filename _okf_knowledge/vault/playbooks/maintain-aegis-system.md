---
type: Playbook
title: Maintain aegis-system
description: MAINTAIN/INGEST playbook — add or update vault knowledge, self-learning write-back (Rung 1 inbox capture → Rung 2 full ingest), cross-links, compile+lint verification.
tags: [aegis-system, ingest, maintenance, okf, procedure, write-back, inbox, self-learn, maintain]
timestamp: 2026-07-18T03:00:00Z
status: active
pack_force_when: [maintain, ingest, write-back, inbox]
---

# Trigger

You need to add or change durable knowledge in aegis-system: a concept, house standard,
playbook, reference, vault script, or Cursor skill — either because a user
asked (MAINTAIN/INGEST) or because a self-learn write-back trigger fired
([AGENTS.md](/AGENTS.md) §1.6 — full trigger/ladder detail in
§ Self-learning write-back below).

# Preconditions

- [AGENTS.md](/AGENTS.md) §1.2 binds all brain mutations to this playbook — follow it end-to-end.
- Read [OKF House Schema](/standards/okf-house-schema.md) for the frontmatter schema before creating files (AGENTS.md §1.3 points there).
- Raw source material (if any) is in [`_inbox/`](/_inbox/) and has not been edited.
- You know which `type` the content is (see decision table below).

# What to create — decision table

| You are documenting… | `type` | Directory | Also update |
|----------------------|--------|-----------|-------------|
| Evergreen knowledge, pattern, tool overview | `Concept` | `vault/` (by domain) | `vault/index.md` |
| House rule (MUST/SHOULD) | `Concept` + tag `standard` | `standards/` | [standards/index.md](/standards/index.md) |
| Executable agent procedure | `Playbook` | `vault/playbooks/` | [playbooks/index.md](/vault/playbooks/index.md) |
| Cached upstream docs | `Reference` | `vault/references/` | Run `kernel/okf.py optimize` |
| Running system in workspace | `System` | `vault/systems/` | [systems/index.md](/vault/systems/index.md) |
| Post-mortem | `Incident` | `vault/incidents/` | Link to affected systems/playbooks |
| Domain routing / tool overview | `Concept` | `vault/concepts/` | [vault/index.md](/vault/index.md) |
| Vault tooling (lint, compile, scrape) | Python script | `kernel/` | This playbook § Scripts |
| Control-plane schema / persona | Markdown | `AGENTS.md` (package root, next to `_okf_knowledge/`) | [_okf_knowledge/index.md](/index.md) |

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
# Optional exceptions (dense catalogs only — see okf-prompt-injection):
# prompt_card_max_chars: 1200          # DBG-309 / enrich clamp override (hard max 2000)
# pack_force_when: [catalog, pin, version]  # force-include in Prompt Pack when query matches
---
```

## 3. Body

- Prefer headings, tables, lists, and fenced code over long prose.
- Standards: normative **MUST** / **SHOULD** / **FORBIDDEN** language.
- Binding standards **MUST** include a non-empty `## Prompt Card` section (default ≤150 tokens / ~600 chars) — enforced by `okf.py lint` (`DBG-308` / `DBG-309`). Override with `prompt_card_max_chars` only when a denser card is justified. See [OKF Prompt Injection](/standards/okf-prompt-injection.md).
- Catalogs that must survive pack eviction **SHOULD** set `pack_force_when: [keywords…]`.
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

The kernel is a single script, `kernel/okf.py`, with one subcommand per operation; it is **not** an OKF concept.

| Subcommand | Role |
|--------|------|
| `okf.py compile` | Regenerate `index.json` + `prompt_cards.json`; embed visualizer graph into `aegis-brain.html` |
| `okf.py lint` | Conformance + broken links + orphans + **standards Prompt Card gate** (stdout + HTML embed) |
| `okf.py card` | Extract `## Prompt Card` sections for slim agent injection |
| `okf.py lookup` | Search via `index.json` (fallback: live vault); list hits or budgeted `--card` |
| `okf.py pack` | Cards-only Prompt Pack export (markdown/json/xml) |
| `okf.py enrich` | LLM gap-fill for retrieval fields (description, tags, `## Prompt Card`); dry-run by default, `--write` to apply |
| `okf.py scrape` | JIT upstream fetch → `vault/` |
| `okf.py optimize` | Normalize references, rebuild vault indexes, run compiler |
| `okf.py serve` | Local visualizer (`aegis-brain.html`) + `POST /api/lint` / `POST /api/compile` |
| `okf.py list` / `show` | Inspect concepts (`--type`, `--raw`, `--card`) |
| `okf.py log-append` | Ephemeral chronology on `log.md` (`--category Decision` etc.) — **not** vault ingest |
| `okf.py doctor` | Setup/health diagnostics (zones, compile artifacts, cards, lint) |
| `okf.py snapshot` / `restore` | Filesystem checkpoints under `.okf-snapshots/` (`restore` needs `--yes`) |

Runtime knobs live in `DEFAULT_OKF_CONFIG` inside `kernel/okf.py`. No `okf.config.json` / `graph.json` / `lint.json` — visualizer data is embedded in `aegis-brain.html`.

**Ephemeral vs durable:** `log-append` / session notes are chronology. Durable knowledge still goes through this playbook (frontmatter + indexes + compile/lint). Do not invent Hermes-style `Decision`/`Session` types in the house taxonomy — use `log-append --category …` or ingest a proper Concept/Incident/Playbook.

# Self-learning write-back (AGENTS.md §1.6 mechanics)

INGEST is not only user-triggered. A turn that produces durable knowledge the vault
does not yet hold MUST close the loop before it ends.

## Triggers (any one fires the loop)

1. The user corrects a fact that a vault card or standard currently states (or omits).
2. Aegis resolved something live that vault-first should have answered — a pin/SHA, version, catalog entry, or upstream behavior (per the freshness rules in [OKF Prompt Injection](/standards/okf-prompt-injection.md)).
3. A troubleshooting/OPERATE task uncovered a root cause worth a post-mortem (`Incident`).
4. Rule #1 lookup returned no relevant card for a domain this brain is supposed to cover (retrieval gap).
5. A procedure was executed that took more than one attempt to get right (playbook candidate).

## Ladder (pick the lowest rung that fits the remaining turn budget)

- **Rung 1 — Capture (minimum, always allowed):** Write one raw note to `_inbox/<date>-<slug>.md` stating what was learned, the evidence grade, and the intended vault destination. No frontmatter or index updates required in `_inbox/`.
- **Rung 2 — Full ingest:** Execute this playbook end-to-end (Path C): correct type/dir, [house-schema](/standards/okf-house-schema.md) frontmatter (`timestamp`, not `last_modified`), cross-links, index updates, `log.md` entry, `compile` + `lint` (0 errors), then archive the `_inbox/` source.

## Rules

1. A turn that fired a trigger MUST NOT end without at least a Rung 1 capture — silently discarding learned knowledge is a governance failure.
2. Rung 1 captures are debt, not storage. Touch `_inbox/` when a write-back trigger fired or the intent is MAINTAIN/INGEST — do **not** sweep inbox on every engineering turn. When you do open `_inbox/` and find untriaged files (anything besides `README.md` / `_archive/`), surface them and offer INGEST.
3. Write-back is exempt from the Mutation Gate — brain mutations gate on this playbook's own verification (`lint` ending `0 error(s)`), not on user approval. Destructive vault operations (deleting/deprecating existing knowledge) still require approval.
4. **Code-structure facts are NOT write-back candidates.** Facts owned by Zone 5 (symbols, resources, manifests, their relationships) are refreshed by regenerating `code/` externally — never hand-write or ingest them into `code/` or the curated vault. Write-back stays for corrections, incidents, procedures, and pins.

# Post-change checklist

Run after **every** concept or playbook add/update:

```bash
# From this package directory (wherever it was dropped in agents/)
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

| Step | Action |
|------|--------|
| 1 | Update affected `index.md` files |
| 2 | Cross-link both directions |
| 3 | Append entry to [log.md](/log.md) |
| 4 | Run `okf.py compile` |
| 5 | Run `okf.py lint` — must end with `0 error(s)` |
| 6 | Archive or delete `_inbox/` source after ingest |

# Verification

- [ ] New/edited file has valid frontmatter per [OKF House Schema](/standards/okf-house-schema.md)
- [ ] Every affected `index.md` lists the new or changed page
- [ ] `python3 _okf_knowledge/kernel/okf.py lint` reports clean (or warnings only, with plan)
- [ ] `log.md` has a dated entry
- [ ] Change followed this playbook as required by [AGENTS.md](/AGENTS.md) §1.2

## Prompt Card

```text
MAINTAIN/INGEST + write-back: type/dir per decision table; required frontmatter;
cross-link both ways; update index.md; log.md. Standards need ## Prompt Card.
Write-back: trigger → Rung 1 `_inbox/<date>-<slug>.md` (min) or Rung 2 full ingest.
No every-turn inbox sweep. After change: okf.py compile then lint (0 errors); archive inbox.
```

# Related

- Maintenance binding: [AGENTS.md](/AGENTS.md) (§1.2, §1.6, MAINTAIN/INGEST intent)
- Schema: [OKF House Schema](/standards/okf-house-schema.md)
- Standards: [Simplicity First](/standards/simplicity-first.md)
- Starter: [Extending Aegis](/vault/concepts/extending-aegis.md)
- Profile template: [Profile schema](/kernel/profiles/_schema.md)
