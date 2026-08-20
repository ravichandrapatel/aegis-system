# 8. Lookup & Prompt Cards

[← Table of contents](README.md)

This is the core “cheap retrieval → slim injection” loop — **Rule #1: Pack First**.

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

## Tool: `okf.py pack` (start here)

One command reports capabilities **and** retrieves cards, so Rule #1 costs a single round-trip:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "prompt injection retrieval"
```

```text
caps: READY | all present | features: rung1_inbox,advisory_explain,prompt_pack,vault_lookup,okf_compile,okf_lint,rung2_maintain,git_ops,okf_v02
# OKF Prompt Pack
query: 'prompt injection retrieval'
cards: 1  total_tokens: 85

### Card: standards/okf-prompt-injection.md (score=168)
…card text…
trust: unverified
related: standards/ide-context-guardrails.md · standards/simplicity-first.md (+1 more)
```

The leading `caps:` line is the whole capability report compressed to one line (`READY` / `BLOCKED`, anything not `present`, and the enabled feature list). It is printed only for `--style markdown`; pass `--no-caps` to suppress it.

The trailing `related:` line is the concept's **graph edges** — see [Traversal](#traversal-following-the-graph). The `trust:` line above it is the derived v0.2 trust tier, printed only when it is a caution — see [Trust labels](#trust-labels-on-cards).

### Empty packs are valid

```bash
python3 _okf_knowledge/kernel/okf.py pack "zzz quantum unicorn dressage"; echo "exit=$?"
```

```text
cards: 0  total_tokens: 0

no relevant cards — the vault has nothing binding on this topic.
Proceed on general engineering judgement; capture anything durable to _okf_knowledge/_inbox/.
To browse rather than search, enter at _okf_knowledge/index.md and follow its links.
exit=0
```

`pack` **always exits 0**. Zero cards is an answer, not an error: hits scoring below `--min-score` are dropped so an off-topic query cannot pull in a confident, irrelevant card. Do not re-run with reworded queries hunting for a hit — browse from `index.md` instead if you want to look around.

## Traversal (following the graph)

Ranking picks the entry points; the graph carries you the rest of the way. This is the part that separates OKF from similarity retrieval: relationships are written down in the markdown before anyone asks a question, so an agent walks to related knowledge deliberately instead of hoping a second query surfaces it.

Every card is followed by the edges `compile` found in that concept's body — by convention its `# Related` section — plus a `source:` line when the concept sets [`resource`](05-frontmatter-schema.md#resource-pointer-to-the-described-thing):

```text
source: https://docs.example.com/api/orders
related: standards/simplicity-first.md · vault/concepts/okf-cognitive-bundle.md (+2 more)
```

| Rule | Detail |
| --- | --- |
| Suppression | Neighbours already in the pack are omitted — every listed path is new reach |
| Cap | 3 links per card (`related_links` in `kernel/src/config.py`; `0` disables) |
| Overflow | `(+N more)` when the concept has further neighbours |
| Budget | Footers are attached **after** card selection, so traversal never displaces a card and never breaks `--budget` |
| Cost | ~8 tokens per link — roughly a 15–30% pack increase, bought deliberately |

**When your cards fall short, open one of those paths — do not re-pack.** Re-querying is the RAG reflex this line exists to replace.

### `pack` flags (reference)

| Flag | Default | Meaning |
| --- | --- | --- |
| `query` | required | Search string for pack assembly |
| `--style` | `markdown` | `markdown` \| `json` \| `xml` |
| `-o` / `--output` | stdout | Write the pack to a file instead |
| `--limit` | 5 | Max ranked hits to consider |
| `--type` | none | Filter by frontmatter type |
| `--max-cards` | 8 | Stop after N cards |
| `--budget` | 1200 | Token budget for the whole pack |
| `--min-score` | 24 | Relevance floor; ranked hits below it are dropped (`0` disables) |
| `--no-caps` | off | Omit the leading capability line |

## Tool: `okf.py lookup`

Use `lookup` when you want the ranked menu or ids rather than an injectable pack.

```bash
# Ranked menu (safe to show agents)
python3 _okf_knowledge/kernel/okf.py lookup "prompt injection"

# Paths only
python3 _okf_knowledge/kernel/okf.py lookup --paths "maintain"

# Prompt Cards for injection (budgeted, no caps line)
python3 _okf_knowledge/kernel/okf.py lookup --card "simplicity"

# Caps / filters
python3 _okf_knowledge/kernel/okf.py lookup --limit 3 --type Concept "okf"
python3 _okf_knowledge/kernel/okf.py lookup --card --max-cards 8 --budget 1200 "kubernetes"
```

### `lookup` flags (reference)

| Flag | Default | Meaning |
| --- | --- | --- |
| `query` | required | Free text matched against id/title/description/tags/type |
| `--paths` | off | Print `concept_id.md` lines only |
| `--card` | off | Emit a budgeted Prompt Pack (cards, or a path stub when a doc has no card) |
| `--json` | off | Machine-readable hits or pack |
| `--limit` | 5 | Max ranked hits |
| `--type` | none | Filter by frontmatter type (e.g. `Playbook`) |
| `--max-cards` | 8 | With `--card`, stop after N cards |
| `--budget` | 1200 | With `--card`, token budget for the pack |
| `--min-score` | 24 | With `--card`, relevance floor (`0` disables) |

Unlike `pack`, `lookup` exits `1` when there are no hits.

### Budget accounting

Token counts come from `tiktoken` (`cl100k_base`) when that optional package is installed, and from a word/punctuation heuristic otherwise — **not** from a `chars // 4` estimate. The budget is enforced strictly: cards are appended until the next one would exceed it, and a first card that cannot fit alone is truncated with a `… (card truncated to fit token budget)` marker.

### Ranking (lexical)

Field weights (tunable constants in `kernel/src/paths.py`): title > id > tags > description > type, with exact / prefix / substring / acronym multipliers and a slug bonus. Optional **graph hop** bonuses come from `kernel/src/graph.json` adjacency (+4 at one hop, +2 at two).

Listing metadata shows `matched=…` and `graph=N hop` for debugging.

### Force-included cards

A concept whose frontmatter lists `pack_force_when` is injected ahead of ranked hits when the query matches. Matching is on **token boundaries**, and multi-word keywords must match as a contiguous phrase — so `tab` no longer fires on “table”, and `deploy` no longer fires on “deployment”. See [Frontmatter schema](05-frontmatter-schema.md#pack_force_when-force-include-keywords).

### Data sources

| Step | Prefers | Fallback |
| --- | --- | --- |
| Candidate list | `index.json` (v2 inverted map) | `rg` over vault markdown, then live `load_vault()` frontmatter |
| Card body | `prompt_cards.json` | Read `.md` + extract `## Prompt Card` |
| Proximity boost | `graph.json` adjacency | No boost |
| `related:` edges | `graph.json` adjacency | No traversal line |

## Trust labels on cards

Most knowledge here is agent-written and then injected as binding rules, so `pack` says so on the card itself. The tier is **derived from `verified` at read time**, never stored:

| `verified` frontmatter | Tier | Card shows |
| --- | --- | --- |
| absent | unverified | `trust: unverified` |
| non-`human:` actors only | machine-confirmed | `trust: machine-confirmed` |
| any `human:` actor | human-reviewed | *(nothing)* |

A card past its `stale_after` date also carries `trust: stale since <date>`, alongside the tier when both apply.

The label is printed **only when it is a caution**. Good standing costs zero tokens, so reviewing a document is what removes its label. Frontmatter detail: [Frontmatter schema — Trust](05-frontmatter-schema.md#trust-generated-verified-and-tiers).

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
| 1 | Detect intent; decide the task is non-trivial |
| 2 | `okf.py pack "<intent keywords>"` — once per task |
| 3 | Read the `caps:` line: `BLOCKED` → stop; `READY` → continue |
| 4 | Inject the returned card text only (an empty pack ends retrieval) |
| 5 | Still short? Follow a `related:` / `source:` edge — traverse, do not re-pack |
| 6 | Generate / validate against the pack — not against fat dumps |

## Retrieval rules (MUST)

1. Pack (or `lookup --card`) when the path is unknown; run it once per task.
2. Do **not** paste whole vault files or compiled artifacts into generation by default.
3. Respect the card/token budgets — the kernel already stops at 8 cards or ~1200 tokens.
4. Treat an empty pack as a finished search, not a failed one.
5. Reach further by **traversing edges**, never by re-running `pack` with reworded queries.

## Related standards

- [`okf-prompt-injection.md`](../_okf_knowledge/standards/okf-prompt-injection.md) — Rule #1 pack / retrieval ladder  
- [`ide-context-guardrails.md`](../_okf_knowledge/standards/ide-context-guardrails.md) — no `@workspace` dumps; `rg` over legacy search  
- [`simplicity-first.md`](../_okf_knowledge/standards/simplicity-first.md) — Laziness Ladder, the design lens applied after the pack  

## Related docs

- [Compiled artifacts](07-compiled-artifacts.md)
- [Kernel tools](09-kernel-tools.md)
- [Pipelines](11-pipelines-and-outputs.md)
