# 9. Lookup & Prompt Cards

[← Table of contents](README.md)

This is the core “cheap retrieval → slim injection” loop (Rule #2).

## Why this exists

| Bad pattern | Cost |
| --- | --- |
| Read hundreds of markdown files into the model | Token burn, missed MUST lines |
| Paste compiled artifacts (`index.json`, graph embeds) or whole standards | Context collapse |
| Grep randomly without ranking | Non-deterministic, slow |

| Good pattern | Benefit |
| --- | --- |
| Score frontmatter via `index.json` | Fast, deterministic |
| Inject only `## Prompt Card` sections | Binding rules stay visible and budgeted |
| Open full docs only when needed | Encyclopedias stay in the vault |

## Tool: `okf.py lookup`

From the package directory:

```bash
# Ranked menu (safe to show agents)
python3 _okf_knowledge/kernel/okf.py lookup "prompt injection"

# Paths only
python3 _okf_knowledge/kernel/okf.py lookup --paths "maintain"

# Prompt Cards for injection (budgeted)
python3 _okf_knowledge/kernel/okf.py lookup --card "simplicity"

# Caps / filters
python3 _okf_knowledge/kernel/okf.py lookup --limit 3 --type Concept "okf"
python3 _okf_knowledge/kernel/okf.py lookup --card --max-cards 8 --budget 1200 "kubernetes"
```

### Flags (reference)

| Flag | Default | Meaning |
| --- | --- | --- |
| `query` | required | Free text matched against id/title/description/tags/type |
| `--paths` | off | Print `concept_id.md` lines only |
| `--card` | off | Emit Prompt Cards for hits |
| `--limit` | 5 | Max ranked hits |
| `--type` | none | Filter by frontmatter type (e.g. `Playbook`) |
| `--max-cards` | 8 | Stop after N cards (protocol normative max) |
| `--budget` | 1200 | Approx token budget for the pack (`chars // 4`) |
| `--all` | off | With `--card`, include path stubs when a card is missing |

### Ranking (lexical)

Field weights (tunable constants in code): title > id > tags > description > type, with exact/prefix/substring multipliers. Optional **graph hop** bonuses from the `index.json` adjacency map.

Listing metadata shows `matched=…` and `graph=N hop` for debugging.

### Data sources

| Step | Prefers | Fallback |
| --- | --- | --- |
| Candidate list | `index.json` | Live `load_vault()` frontmatter |
| Card body | `prompt_cards.json` | Read `.md` + extract `## Prompt Card` |
| Proximity | `index.json` adjacency | No boost |

## Tool: `okf.py card`

Extract cards when you already know paths:

```bash
python3 _okf_knowledge/kernel/okf.py card standards/simplicity-first.md
python3 _okf_knowledge/kernel/okf.py card --max-chars 600 path1.md path2.md
```

Exits non-zero if any file lacks a Prompt Card.

## Writing a good Prompt Card

Place under a `## Prompt Card` heading. Prefer a short fenced block whose body stays ≤ ~150 tokens (~600 chars):

- Heading: `## Prompt Card`
- Body: binding MUST / SHOULD / FORBIDDEN lines only
- Leave encyclopedic tables and citations in the full document body

| Guidance | Detail |
| --- | --- |
| Length | Target ≤ 150 tokens (~600 chars) |
| Content | Binding rules only — not full tables or citations |
| Audience | The **generation** turn |
| Full doc | Remains in vault for deep lookup |

Standards without a card fail lint (`DBG-308`).

## Prompt Pack assembly procedure

| Step | Action |
| ---: | --- |
| 1 | Detect intent + load Profile; pass capability check |
| 2 | `okf.py lookup "<intent>"` → shortlist concept ids |
| 3 | Traverse graph for dependencies; merge candidates |
| 4 | Evict to ≤ 8 cards using protocol sort order |
| 5 | `okf.py lookup --card …` or `okf.py card` for winners |
| 6 | Generate / validate against the pack — not against fat dumps |

## Protocol rules (MUST)

1. Locate knowledge with lookup when the path is unknown.  
2. Do **not** paste whole vault files or compiled artifacts into generation by default.  
3. Respect card/token budgets; stop expanding when the budget is hit.  
4. Eviction tier: `Standards > Playbooks > Systems/Concepts > References > Code`. Zone 5 `Code` cards fill remaining slots only — pack assembly sorts them after every curated hit, so they can never crowd curated cards out of the budget.

## Related standards

- [`okf-prompt-injection.md`](../_okf_knowledge/standards/okf-prompt-injection.md) — Rule #2  
- [`simplicity-first.md`](../_okf_knowledge/standards/simplicity-first.md) — Rule #1  

## Related docs

- [Compiled artifacts](08-compiled-artifacts.md)
- [Kernel tools](10-kernel-tools.md)
- [Pipelines](12-pipelines-and-outputs.md)
