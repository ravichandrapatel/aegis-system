---
name: okf-pack
description: >-
  Build an OKF Prompt Pack (OKF Rule #1 — Pack First). Use before planning,
  generation, or multi-file edits; or when the user asks to pack/lookup.
---

One command reports capabilities **and** retrieves cards. Inject **only** `## Prompt Card` text. Ladder + budgets: [`okf-prompt-injection.md`](../../../_okf_knowledge/standards/okf-prompt-injection.md). DNA: [`AGENTS.md`](../../../AGENTS.md) § Rule #1.

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"
```

Output starts with `caps: READY | ... | features: ...`, then the cards.

## Reading the result

- **Cards returned** — they bind. Follow them over your own assumptions.
- **Empty pack** — a valid answer meaning the vault holds nothing binding here. Proceed on general engineering judgement and note anything durable for `_inbox/`. Do **not** re-run with reworded queries hunting for a hit. To browse by hand, enter at `_okf_knowledge/index.md`.
- **`caps: BLOCKED`** — stop on non-trivial create/modify; report the missing capability.

Run once per task, not per message.

## Traversing on

Cards end with the concept's graph edges — neighbours not already in the pack, plus `source:` when the concept records a `resource`:

```text
related: standards/simplicity-first.md · vault/concepts/okf-cognitive-bundle.md (+2 more)
```

When your cards fall short, **open one of those paths**. Do not re-pack: ranking picked the entry points, and the edges are how you reach the rest of the bundle.

## Options

- `--min-score N` — relevance floor (default 24; `0` disables and restores every weak match).
- `--no-caps` — omit the capability line.
- `--style json|xml` — machine-readable pack.

## After pack

`grill-me` if branching decisions remain → `mutation-gate` if high-risk → `okf-writeback` for gaps.

**FORBIDDEN:** claiming compliance without a pack when the Brain is available; pasting `index.json`, `graph.json`, or full document bodies.
