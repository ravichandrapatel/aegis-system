---
type: Concept
title: OKF Prompt Injection
description: Binding rule — anytime Aegis runs, inject a dynamic Prompt Pack from live lookup; vault-first catalogs with live refresh when stale; grader reads only for explain/fix — not a static path ban-list.
tags: [standard, okf, prompting, tokens, aegis, retrieval, cache]
timestamp: 2026-07-18T02:45:00Z
status: active
---

# OKF Prompt Injection (Rule #2)

**Rule #2.** Curated OKF stays in the vault. Generation and Q&A context get a **dynamic Prompt Pack**: slim `## Prompt Card` text from **this turn’s** `okf.py lookup` / `okf.py card` — not a full-brain dump and not a static “never open these paths” encyclopedia in AGENTS.md.

**Scope:** Anytime Aegis is used (questions, review, authoring) — not only Path A artifact generation.

Domain graders differ by stack. **What is in-bounds for a turn is defined by the live lookup hit-set** (and, for benches, by task placeholders such as `GATE_ANSWER_KEY_GLOBS`).

## Retrieval ladder (global)

| Priority | Lane | How | Use for | Must not use for |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **OKF knowledge cache** | `okf.py lookup --card` (+ ≤1 follow-up `lookup`/`card`) | Standards, playbooks, concepts, catalogs, pins/versions in the vault | Random vault Grep; paste compiled artifacts / full docs |
| 2 | **Pointers from cards** | Read only paths the **current cards** name | One deep dive the pack pointed to | Opening every related file |
| 3 | **Task corpus** | Glob → Grep → Read (or Explore subagent) | Product/code/config being changed or inspected | Discovering org compliance that should be on cards |
| 4 | **Grader / answer key** | See [Grader access](#grader-access-daily-work) | Explain failure (what/why/where); fix from gate output | Authoring-time peek to invent compliance |

Lane 1 **MUST** run before vault Grep or authoring. Corpus Grep (lane 3) is allowed after lane 1; it is not a substitute for lane 1.

## Catalog / pin freshness (vault + live)

Pins, version catalogs, and similar reference data use **both** sources, ordered by freshness need:

1. **Vault first (default):** human-maintained Prompt Cards; keep warm with `okf.py compile` (`index.json` / `prompt_cards.json`; process also mtime-caches them).
2. **Live fetch when stale or missing:** network/`gh`/upstream only if the card is absent, marked stale, or the user requires verification against current upstream.
3. **Write-back (SHOULD):** durable discoveries belong back in the vault via the maintain playbook — do not rediscover every run.

Agents **MUST NOT** default to live rediscovery when a current card already supplies the catalog.

## Grader access (daily work)

| Mode | Policy / Rego / CI rule sources |
| :--- | :--- |
| **Authoring / writing** | Cards (+ failure text if remediating). **MUST NOT** mine the grader to invent compliance. |
| **Asked what failed / why / where** | **MAY** open the relevant grader source to explain and locate the rule. Prefer starting from failure output, then open the cited file/rule. |
| **A/B bench OKF arm** | Follow the bench prompt: forbidden globs are **task-specific** (`GATE_ANSWER_KEY_GLOBS`), not this standard’s static list. |

## MUST

1. Anytime Aegis is used, run `okf.py lookup --card` (or `lookup` then `card` / `pack`) with **task-specific** keywords before vault Grep or generation.
2. Assemble a **Prompt Pack** from returned `## Prompt Card` sections only.
3. Each card **MUST** target **≤150 tokens** (~600 characters) by default. Prefer shorter.
4. Hard pack rule: **≤8 Prompt Cards**. Target budget **≈1200 tokens** (guidance — tokenizers differ; kernel default matches). Prefer fewer/shorter when the hit-set allows.
5. Encyclopedic bodies **MUST** stay in the vault — **MUST NOT** be copied wholesale into the generation prompt.
6. Binding rules **MUST** expose a `## Prompt Card` so lookup can surface them dynamically.
7. Missing pin/version/constraint in the pack → **one** follow-up `lookup`/`card`, then act (or live-refresh per freshness rules above).

## Prompt Card exceptions (frontmatter)

Dense catalogs MAY declare exceptions — default ≤600 remains the norm:

| Field | Effect |
| :--- | :--- |
| `prompt_card_max_chars: N` | Raises the DBG-309 lint / enrich clamp for that doc only (hard ceiling **2000**). |
| `pack_force_when: [keywords…]` | When the query shares any keyword, the card is force-included first and **bypasses** pack `max_cards` + token budget (kernel safety cap: 4 forced cards). |

Example:

```yaml
prompt_card_max_chars: 1200
pack_force_when: [catalog, pin, version]
```

## SHOULD

1. `okf.py card <path>…` when paths are already known from lookup.
2. Prefer **one-shot validation pass** when the Prompt Pack already encodes binding rules — avoid generate → fail → remediate loops when the first pack is sufficient.
3. Keep domain catalogs/pins **on cards** so vault-first stays viable. Prefer a vault reference (or card) for version/pin facts over live rediscovery every turn. Use `pack_force_when` so dense catalog cards survive pack eviction.
4. For authoring tasks, keep the pack to **MUST bullets + concrete facts** only (still ≤150 tok/card unless `prompt_card_max_chars` justifies more).
5. After vault edits: `okf.py compile` (and lint) so the knowledge cache stays fresh.

## FORBIDDEN

1. Pasting compiled artifacts (`index.json`, graph embeds) or full standard/concept files into the prompt by default.
2. “Load the whole Aegis brain” as the default strategy.
3. Skipping live lookup and grepping the vault for compliance knowledge.
4. Encoding a **static** forever ban/allow of domain grader paths in AGENTS.md (bench/task prompts or domain cards own isolation globs).
5. Authoring-time reverse-engineering of the grader when the Prompt Pack already covers the task.
6. Preferring live pin/catalog rediscovery every run when a fresh vault card exists.
7. Treating “no OKF is faster” as truth without measuring **time to validation pass** (include remediation turns).

## Example minimal pack (domain-agnostic)

```text
Rule #1: simplest shortest minimal solution that works.
Rule #2: lookup --card / pack first; inject cards only (≤150 tok/card; ≤8 cards; ≈1200 tok).
New durable knowledge: frontmatter + maintain-aegis-system playbook; compile+lint.
Catalogs: vault-first; live fetch only if stale/missing; write back.
```

## Prompt Card

```text
Anytime Aegis: lookup --card / pack first (≤8 cards; ≈1200 tok; cards ≤150 tok / 600 chars).
Exceptions: prompt_card_max_chars (≤2000); pack_force_when force-includes (≤4).
Ladder: OKF cache → card pointers → task corpus Grep → grader only for explain/fix.
Catalogs: vault-first on cards; live only if stale/missing; write back.
FORBIDDEN: brain dump; skip lookup; static path bans in AGENTS.md.
```

## How to load knowledge (procedure)

| Step | Action |
| :--- | :--- |
| 1 | Form `<task keywords>` from **current** intent/domain |
| 2 | `okf.py lookup --card --limit 3 "<task keywords>"` |
| 3 | Inject returned cards only |
| 4 | Optional: one follow-up lookup/card or live refresh if stale/missing |
| 5 | Corpus Glob/Grep/Read as needed for the task files |
| 6 | On gate failure: use failure text; open grader sources when explaining what/why/where |
| 7 | Durable new catalog facts → maintain playbook → `compile` |

## Bench / isolation note

A/B benches that isolate “cards vs grader” **MUST** name forbidden answer-key globs in the **bench prompt** (e.g. `{{GATE_ANSWER_KEY_GLOBS}}`). Do not bake those globs into AGENTS.md.

## Related

- Principle: [Simplicity First](/standards/simplicity-first.md)
- Control plane: [AGENTS.md](/AGENTS.md) Rule #1 (thin pointer)
- Playbook: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Starter: [Extending Aegis](/vault/concepts/extending-aegis.md)
