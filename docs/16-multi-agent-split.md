# 16. Optional future: multi-agent split of `AGENTS.md`

[← Table of contents](README.md)

**Status:** Directional only — **not implemented**.  
**Shipping truth today:** a single root [`../AGENTS.md`](../AGENTS.md).

This page is the human operator guide for the *optional* enhancement: exposing Aegis as multiple IDE agents while keeping **one brain**.

---

## Table of contents (this page)

1. [What problem this solves](#1-what-problem-this-solves)
2. [What we will not do](#2-what-we-will-not-do)
3. [Proposed entrypoints](#3-proposed-entrypoints)
4. [Profiles vs agent files](#4-profiles-vs-agent-files)
5. [Invariants checklist](#5-invariants-checklist)
6. [Trigger criteria (when to split)](#6-trigger-criteria-when-to-split)
7. [Migration sketch](#7-migration-sketch)
8. [Until then](#8-until-then)

---

## 1. What problem this solves

A unified `AGENTS.md` (Path A + B + C + maintain + schema + budgets) is correct for a **single** control-plane contract, but it can:

| Cost | Effect |
| --- | --- |
| Context tax | Protocol competes with Prompt Cards every turn |
| Role noise | Deploy operators see Generation Report gates they do not need |
| Mis-routing | Agents may blend Path A planning into Path C execution |
| IDE UX | Users cannot pick “Aegis Maintain” vs “Aegis Generate” explicitly |

A **split** means multiple selectable agent files that each load a **smaller pipeline contract**, still sharing `_okf_knowledge/`.

## 2. What we will not do

| Anti-pattern | Why forbidden |
| --- | --- |
| Fork a brain per agent | Divergent standards, broken graph, unmaintainable |
| Copy-paste full protocol into each agent | Drift; burns tokens |
| Replace Profiles with agent names alone | Profiles gate **capabilities**; agents gate **pipeline shape** |
| Split before pain is proven | Violates Laziness Ladder (Rule #1) |

## 3. Proposed entrypoints

Illustrative layout:

```text
aegis-system/
├── AGENTS.md              # thin router + handoff
├── agents/
│   ├── _common.md         # shared MUST (lookup, cards, precedence, exit codes)
│   ├── generate.md        # Path A
│   ├── validate.md        # Path B
│   ├── execute.md         # Path C (deploy/upgrade/rollback)
│   └── maintain.md        # MAINTAIN / INGEST
└── _okf_knowledge/        # single shared brain
```

| Entrypoint | Intents | Output contract |
| --- | --- | --- |
| Router `AGENTS.md` | All (detect → hand off) | Thin; may only route |
| `generate.md` | CREATE / MODIFY / MIGRATE | Generation Report |
| `validate.md` | REVIEW / OPERATE / TROUBLESHOOT | Architectural Review |
| `execute.md` | DEPLOY / UPGRADE / ROLLBACK | Execution Plan |
| `maintain.md` | MAINTAIN / INGEST | Execution Plan + maintain playbook |

## 4. Profiles vs agent files

| Mechanism | Answers |
| --- | --- |
| **Agent entrypoint** | Which **pipeline** contract is loaded? |
| **Profile** (`kernel/profiles/`) | Which **modules / vendors / standards** may load? |

Example: invoke **Generate** agent + **architect** Profile.

Do not collapse these into one dimension.

## 5. Invariants checklist

Before merging any split, verify:

- [ ] One `_okf_knowledge/` for all agents  
- [ ] Shared lookup + Prompt Card rules (Rule #2)  
- [ ] Shared knowledge precedence + evidence grades  
- [ ] Shared pack budget (≤ 8 cards hard; target ≈1200 tokens)  
- [ ] MAINTAIN still binds to `maintain-aegis-system.md`  
- [ ] Capability check stays the shared `AGENTS.md` §4.1 gate — required standards/evidence from the Prompt Pack present, else exit `4`; Profiles remain optional schema, orthogonal to agent files  
- [ ] Shared MUST lives in one place (`_common.md` or thin root) — no contradictory copies  
- [ ] `docs/` + README updated for multi-agent IDE registration  

## 6. Trigger criteria (when to split)

Split only if **most** are true:

| Signal | Guidance |
| --- | --- |
| Protocol length hurts | Unified file regularly crowds out Prompt Pack |
| Mis-routing observed | Wrong Path steps applied repeatedly |
| Team demand | Roles want distinct selectable agents |
| Edit collisions | Changing Path A regularly risks Path C drift |

Otherwise keep the monolith.

## 7. Migration sketch

1. Extract shared MUST → `agents/_common.md`.  
2. Move Path sections into specialized files; thin the root router.  
3. Register multiple IDE agents pointing at those files (same package root).  
4. Add a checklist/lint: every specialized agent references `_common.md`.  
5. Recompile/lint brain unchanged — **no** per-agent compiled artifacts (`index.json` / `prompt_cards.json` / HTML embed).

### Contract delivery (open design question)

Static `agents/*.md` + `_common.md` has an unresolved mechanism problem: IDE agent files do **not** transclude other files. Each specialized agent must either instruct the model to read `_common.md` (one extra tool call every turn — the very context tax the split is meant to remove) or paste the shared MUSTs (the drift this page forbids, policed only by a lint).

**Preferred future shape (OpenSpec-style runtime delivery):** keep the thin root router and have `okf.py` serve the per-path contract on demand (e.g. `okf.py contract generate`), the way `openspec instructions <artifact>` serves stage instructions from one schema. One source of truth, zero copies, no `_common.md`, no reference-lint. Evaluate this before committing to static agent files.

## 8. Until then

| Do this today | Not that |
| --- | --- |
| Use intent matrix + Profiles | Invent parallel protocols |
| Use Path A/B/C sections inside one `AGENTS.md` | Duplicate vaults |
| Keep Prompt Packs slim | Paste full `AGENTS.md` into generation turns |

See also: [Protocol & routing](06-protocol-routing.md), [Profiles](07-profiles.md), [Pipelines](12-pipelines-and-outputs.md).
