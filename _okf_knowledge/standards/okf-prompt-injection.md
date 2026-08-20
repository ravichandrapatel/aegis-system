---
type: Concept
title: OKF Prompt Injection
description: Rule #1 pack — inject slim Prompt Cards; retrieval ladder OKF → corpus → live → write-back.
tags: [standard, okf, prompting, tokens, pack, retrieval]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
---

# OKF Prompt Injection

Implements **Rule #1 — Pack first** from [AGENTS.md](/AGENTS.md).

Curated OKF stays in the vault. Generation context gets a **dynamic Prompt Pack**: slim `## Prompt Card` text from this task’s `okf.py pack` — not a full-brain dump. `pack` also prints a one-line `caps:` header, so Capability Discovery and retrieval cost a single command.

## Retrieval ladder

| Priority | Lane | How | Use for |
| :---: | :--- | :--- | :--- |
| 1 | OKF | `okf.py pack` | Standards, playbooks, catalogs, pins on cards (+ `caps:` line) |
| 2 | Traverse | Follow a card's `related:` / `source:` line | One deep dive |
| 3 | Task corpus | Glob → **ripgrep (`rg`)** → Read | Product code in this repository (never legacy `grep`) |
| 4 | Live external | Official Git/OCI/`gh` | Pins still missing/stale after 1–3 |
| 5 | Grader | Only to explain/fix a failure | Not for inventing compliance at author time |

Lane 1 **MUST** run before corpus or authoring — once per task, not per message. Write-back durable pins/recipes to `_inbox/` (Rung 1); ingest via maintain playbook.

**FORBIDDEN:** paste `graph.json` / full standards into the prompt; skip pack and grep the vault for compliance; invent stub designs that omit wiring the current Prompt Pack requires.

## Traversal (lane 2)

Ranking picks the entry points; the **graph** carries you the rest of the way. Every card ends with the edges `compile` found in that concept's body (by convention, its `# Related` section):

```text
source: https://upstream.example/docs/thing     # only when frontmatter sets `resource`
related: standards/simplicity-first.md · vault/concepts/okf-cognitive-bundle.md (+2 more)
```

Neighbours already in the pack are omitted, so every path listed is genuinely new reach. Open one **only** when the cards you hold do not answer the question — this is deliberate traversal, not a second search. Re-running `pack` instead of following an edge is the mistake this line exists to prevent.

When the pack is empty, `_okf_knowledge/index.md` is the entry point for browsing the bundle by hand.

## Empty packs

An empty pack is a **valid answer**: the vault holds nothing binding on this topic. Drop to lane 3 and proceed on general engineering judgement, then note anything durable for `_inbox/`. Re-running `pack` with reworded queries to force a hit is **FORBIDDEN** — it burns turns and invites an irrelevant card.

Ranked hits below `--min-score` (default 24) are dropped for this reason: a confidently-injected wrong card is worse than no card, because cards outrank the model's own judgement.

## Budgets

- Each card **SHOULD** be ≤ ~600 characters (~150 tokens); lint warns above it.
- A pack is capped at 8 cards and the `--budget` token ceiling (default ~1200). Cards are added in rank order until either limit is reached; a single oversized card is truncated rather than allowed to exceed the budget.
- Concepts may set `pack_force_when: [keywords]`. Matching is on **token boundaries**, and multi-word keywords must appear as a contiguous phrase — so `tab` does not fire on `table`, and `deploy` does not fire on `deployment`.
- `related:` lines cost ~8 tokens per link and are attached **after** card selection, so traversal never displaces a card. Set `related_links: 0` in `okf/config.py` to disable.

## Prompt Card

```text
Rule #1: okf.py pack before authoring — it prints caps + cards in one command.
Inject ## Prompt Card text only; empty pack is valid, do not re-query for a hit.
Need more? Follow a card's related:/source: edge — do not re-pack. Empty: index.md.
Ladder: OKF → traverse edges → repo corpus (rg) → live upstream → write-back _inbox.
No graph/index/full-doc paste; no grader mining to invent compliance.
```

# Related

- DNA: [AGENTS.md](/AGENTS.md)
- Schema: [OKF House Schema](okf-house-schema.md)
- IDE tokens: [IDE Context Guardrails](ide-context-guardrails.md)
- Pins / caches: [`vault/references/`](/vault/references/) (populate via scrape + maintain)
