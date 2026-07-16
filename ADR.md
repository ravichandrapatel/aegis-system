# ADR-0001: Aegis Control Plane Architecture

| Field | Value |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-07-13 |
| **Package** | `aegis-system` |
| **Protocol** | [`AGENTS.md`](AGENTS.md) v4.6.1 |
| **Brain** | [`_okf_knowledge/`](_okf_knowledge/) |

This document is the **full Architecture Decision Record** for aegis-system. It lives **outside** `_okf_knowledge/` (same level as `README.md`) so humans can read the “why” without treating the ADR as agent prompt fuel. Binding agent behavior remains in `AGENTS.md` and vault standards/playbooks.

---

## 1. What Aegis is (and is not)

### What it is

Aegis is a **portable engineering control plane for AI coding agents**:

1. **`AGENTS.md`** — immutable protocol: how the agent routes intent, enforces governance, assembles prompts, and maintains knowledge.
2. **`_okf_knowledge/`** — the “brain”: curated Open Knowledge Format (OKF) markdown with typed frontmatter, plus small Python kernel tools (lookup, lint, graph compile, serve).

Together they zip into an IDE agents/skills folder and travel with the team.

### What it is not

| Not this | Why that matters |
| --- | --- |
| An AST / tree-sitter **code indexer** | That is the job of tools like [okf-generator](https://github.com/UmairBaig8/okf-generator). Aegis stores **operational and policy knowledge**, not one card per function. |
| A vector RAG store | Lookup is deterministic over frontmatter (title/tags/path), not embeddings. |
| A replacement for project source | Source trees stay untouched; the brain is a **sibling knowledge package**. |
| A prompt dump of the whole vault | Agents must **lookup → Prompt Card**, not paste `graph.json` or entire standards. |

### Design goal in one sentence

**Find the right knowledge cheaply, inject only what is needed to generate or validate, keep the brain reviewable and maintainable.**

---

## 2. Problem statement

Without a control plane, agents repeatedly:

1. **Burn tokens** re-reading large standards and playbooks every turn.
2. **Miss the binding rule** because it was buried in a fat paste or never opened.
3. **Invent layout** — docs scattered with no type, no index, no audit trail.
4. **Confuse indexes with knowledge** — treating a compiled catalog (`context.toon`, historically) as something to stuff into the model.

We needed decisions that make the *cheap path* the *correct path*.

---

## 3. Decision drivers

1. **Token budget** — default generation Prompt Pack should stay small (cards ≤ ~150 tokens each; pack SHOULD ≤ ~400 tokens).
2. **Reviewability** — knowledge is git-friendly markdown humans can PR.
3. **Stable identity** — every doc has a path/id agents can resolve after lookup.
4. **Auditability** — mutations leave `log.md`, pass lint, refresh graph for the visualizer.
5. **Portability** — no database, no cloud dependency for core routing; stdlib Python where possible.
6. **Separation of lanes** — curated ops/policy knowledge must not be drowned by optional future code-symbol indexes.

---

## 4. Decisions (in depth)

### D1 — Portable dual root: `AGENTS.md` + `_okf_knowledge/`

#### Decision

Ship Aegis as **one folder** containing:

- `AGENTS.md` — control-plane contract (how to think / route).
- `_okf_knowledge/` — knowledge + kernel tools (what is known / how to query it).

#### Why built this way

Agents need both an **immutable policy surface** and a **mutable memory**. If protocol lives only in chat instructions, it drifts. If knowledge lives only in a random `docs/` tree with no protocol, agents do not know the maintenance or injection rules.

Keeping them as siblings makes the package **zippable**: drop into `.cursor/agents/`, `.github/agents/`, etc., without installing a service.

#### What it is used for

| Consumer | Use |
| --- | --- |
| IDE agent | Loads `AGENTS.md` as the agent definition; reads/writes under `_okf_knowledge/`. |
| Humans | README points here; ADR (this file) explains architecture. |
| CI / maintain | Scripts run relative to package root. |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Protocol-only (no vault) | No durable, typed memory; every team reinvents docs. |
| Vault-only (no AGENTS.md) | No binding routing / injection rules. |
| Central SaaS brain | Breaks air-gap / local-first; heavier adoption. |

---

### D2 — Four-zone brain under `_okf_knowledge/`

#### Decision

| Zone | Path | Role |
| --- | --- | --- |
| 1 | `_inbox/` | Untriaged raw material (immutable until ingested) |
| 2 | `kernel/` | Execution: Python tools (+ optional Profiles schema) |
| 3 | `standards/` | Binding MUST/SHOULD house rules |
| 4 | `vault/` | Passive memory: Concepts, Playbooks, Systems, Incidents, References |

#### Why built this way

Mixing “law,” “how-to,” “scratch,” and “scripts” in one flat folder causes:

- Agents treating drafts as standards.
- Encyclopedic product docs mixed into the kernel tooling tree.
- No clear ingest funnel.

Zones encode **lifecycle and authority**: inbox → curated vault/standards; kernel runs tools and domain execution docs; standards bind governance.

#### What it is used for

| Zone | Day-to-day use |
| --- | --- |
| `_inbox/` | Drop notes, logs, exports before MAINTAIN/INGEST. |
| `kernel/*.py` | `okf_lookup`, lint, graph compile, serve UI. |
| `standards/` | Governance Engine inputs — **simplicity-first**, **okf-prompt-injection**, **metadata-headers** (plus any domain standards you add). |
| `vault/` | Playbooks agents follow; concepts humans/agents reference. |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Type-only folders with no inbox | No safe staging for raw dumps. |
| Everything under `vault/` | Scripts and law lose privilege / clarity. |
| Wiki / Notion external brain | Weak agent filesystem access; poor offline story. |

---

### D3 — OKF frontmatter as the house schema

#### Decision

Every durable markdown concept **MUST** carry YAML frontmatter, for example:

```yaml
---
type: Playbook
title: Maintain aegis-system
description: How to add or update concepts, playbooks, and standards in the vault
tags: [aegis-system, ingest, maintenance]
timestamp: 2026-07-13T14:50:00Z
status: active
---
```

Known types: `Concept`, `Playbook`, `System`, `Incident`, `Reference`, `Profile` (optional).  
Enforced/warned by `kernel/okf.py lint`.

#### Why built this way

Agents and tools need **machine-readable identity** without a DB:

- Lookup ranks on title/description/tags/type/path.
- Lint checks required fields and broken links.
- Graph compile builds nodes from the same metadata + body links.

Plain markdown without frontmatter forces brittle path heuristics.

#### What it is used for

| Tool / flow | Use of frontmatter |
| --- | --- |
| `okf.py lookup` | Scoring and hit listing |
| `okf.py lint` | Schema + health |
| `okf.py compile` | Node labels/types in `graph.json` |
| Humans | Skim type/status in PRs |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Filename conventions only | Too weak for tags/status/description. |
| JSON/YAML sidecars | Doubles files; easy desync. |
| Full OKF-generator symbol schema | Overkill for curated ops docs; wrong granularity. |

---

### D4 — Lookup + Prompt Cards; remove fat index injection (`context.toon`)

#### Decision

1. Agents **MUST** find vault files with:

   ```bash
   python3 _okf_knowledge/kernel/okf.py lookup "<query>"
   ```

   Flags: `--paths` (locations only), `--card` (Prompt Cards), `--limit N`.

2. For generation, inject **`## Prompt Card` sections only** (Rule #2 / OKF Prompt Injection standard). Pack SHOULD stay ≤ ~400 tokens.

3. **`context.toon` is deleted and must not return.** Agents must not paste `graph.json` or whole standards by default.

Normative: `AGENTS.md` §1.4–1.5 and `_okf_knowledge/standards/okf-prompt-injection.md`.

#### Why built this way

**Failure mode observed:** “Load the brain” / paste compiled TOON or full standards → high tokens, weak compliance, slow validation loops.

**Fix:** Ranked discovery (lookup) + **slim, author-maintained cards** that encode only binding MUST lines. Encyclopedic detail stays on disk for optional deep reads (e.g. full playbook steps), not for every authoring turn.

Removing `context.toon` eliminates a tempting fat paste target. The catalog is replaced by **live lookup over source markdown**.

#### What it is used for

| Command / artifact | Use |
| --- | --- |
| `okf.py lookup "prompt injection"` | Find `standards/okf-prompt-injection` etc. |
| `--paths` | Resolve filesystem path for Read tools |
| `--card` | Build Path A Prompt Pack |
| `okf.py card <paths>` | Extract cards when paths already known |
| Prompt Card in each standard | Durable, reviewable injection surface |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Keep `context.toon` as agent context | Recreates fat-dump tax; stale vs files. |
| Always paste full playbook | Exceeds token budget; drowns the MUST lines. |
| Embeddings / RAG | Extra infra; approximate retrieval; worse for exact standards. |

---

### D11 — Split knowledge cache vs corpus search (architecture enhancement on D4)

> **ADR role:** record design choice, trade-offs, and future direction only.  
> **Not** agent operating procedure — that lives in `_okf_knowledge/standards/okf-prompt-injection.md`.

#### Context / issue

Agents were treating the vault and CI graders as just another Grep corpus. That fights D4 (lookup + Prompt Cards): high turn cost, weak use of `compile` artifacts, and temptation to put domain path bans into `AGENTS.md`.

#### Architecture decision

1. **Two retrieval surfaces (structural):**
   - **Knowledge plane** — OKF vault + compiled `index.json` / `prompt_cards.json` + `okf.py lookup` (curated, cacheable).
   - **Corpus plane** — task workspace via Glob/Grep/Read (live product code/config).
2. **Warm cache is compile output**, not ad-hoc vault walks every turn. Kernel may mtime-cache those JSON files in-process.
3. **Catalog freshness model:** vault is the durable cache; live upstream fetch is a refresh path when data is stale/missing; durable results write back through the maintain playbook (same as other brain mutations).
4. **Control-plane thinness:** `AGENTS.md` stays a short pointer. Domain grader isolation (e.g. bench answer-key globs) is a **task/bench concern**, not a forever list in the control plane or this ADR’s body.
5. **Future:** optional separate code-index lane remains D8; do not merge into default vault lookup.

#### Consequences

| Improves | Watch |
| --- | --- |
| Clear home for curated vs live search | Cards must carry catalogs or agents will Grep again |
| Aligns with industry “agentic Grep for code, packs for policy” | Maintainers must `compile` after vault catalog updates |
| Keeps ADR / AGENTS out of per-domain path ban lists | Bench prompts own isolation globs |

#### Normative behavior (pointer only)

Agent-facing MUST/SHOULD for ladders, freshness order, and when grader files may be opened: **`standards/okf-prompt-injection.md`** only.

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Encode full retrieval procedure in ADR or AGENTS.md | Wrong doc type; ADR is design history, AGENTS must stay thin |
| Default vector RAG over the vault | Extra infra; worse for exact standards; duplicates OKF cards |
| No compiled index (always live walk) | Slower lookup; wastes the compile pipeline from D5 |

---

### D12 — Kernel ergonomics inspired by repo-packers (not becoming one)

> **ADR role:** design choice only. Agent procedure stays in `okf-prompt-injection.md` / `AGENTS.md`.

#### Context / issue

Tools like [Repomix](https://github.com/yamadashy/repomix) excel at packing **source trees** into AI-friendly blobs (token counts, ignore files, secretlint, XML/JSON/MD export, MCP). Aegis `okf.py` had overlapping *needs* (budget math, safe ingest, machine API) but a **different job**: curated Prompt Packs over an OKF vault — never full-brain dumps.

#### Decision

Enhance `okf.py` **v1.2** with Repomix-adjacent capabilities that preserve OKF semantics:

| Capability | Behavior |
| --- | --- |
| Token budgets | Prefer `tiktoken` `cl100k_base` when installed; else improved heuristic (not raw `chars//4` only) |
| Secret scan | Block `scrape` / Reference writes on common credential patterns (`DBG-403`) |
| Ignore | `.okfignore` (+ optional `.gitignore`) filters concept walks |
| Config | `okf.config.json` for max_cards, token_budget, compress, secret_scan |
| Pack export | `okf.py pack` → markdown \| json \| xml of **cards only** |
| Machine API | `lookup --json` for agents/CI |
| Compress | Structure-preserving Reference trim (headings + short bodies) |
| Dedup | Single `assemble_prompt_pack()` shared by `lookup --card` and `pack` |

#### Benefits

1. **Honest budgets** — pack eviction matches real LLM token cost when tiktoken is present.
2. **Safer ingest** — scraped upstream cannot silently land secrets in the vault.
3. **Faster / cleaner walks** — ignore noise (`_archive`, tmp) without hardcoding every path.
4. **Agent integration** — `--json` / `pack` give stable machine output without scraping prose.
5. **Repomix formats without Repomix anti-pattern** — XML/MD/JSON export of the Prompt Pack only; corpus packing stays out of band (use Repomix/Grep for code).
6. **Less duplicate work** — one pack assembler; config defaults once.

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Make `okf.py pack` dump the whole vault/repo | Contradicts D4 / Rule #2 |
| Require Node/Secretlint/Tree-sitter always | Breaks stdlib-first portability; optional tiktoken is enough |
| Encode packer UX into AGENTS.md | Wrong layer; keep DNA thin |

#### Normative home

Runtime flags/config: `kernel/okf.py` + optional `okf.config.json` / `.okfignore`. Agent injection rules unchanged.

---

### D5 — `graph.json` is a visualizer/tooling artifact, not agent context

#### Decision

- `kernel/okf.py compile` (renamed from `toon_compiler.py`) walks the vault, builds **nodes/edges** from frontmatter + markdown links, writes `graph.json` plus slim `index.json` / `prompt_cards.json` for `okf_lookup`, and embeds into `aegis-brain.html`.
- `okf.py lint` writes `lint.json` (also embeddable).
- `okf.py serve` exposes `POST /api/compile` and `POST /api/lint` so the UI can regenerate without hand-editing JSON.
- Agents **MUST NOT** load `graph.json` into generation prompts.

#### Why built this way

Humans need a map of how concepts link (brain HTML). Agents need **ranked text cards**, not a multi-thousand-token JSON graph.

Compiling a graph also validates that cross-links resolve (together with lint). Separating “compile for viz” from “inject for LLM” prevents category errors.

On-disk JSON remains useful for **offline `file://` HTML**, CI, and maintain checklists even when the server can regenerate on demand.

#### What it is used for

| Artifact / API | Use |
| --- | --- |
| `graph.json` | Brain visualizer; dependency browsing |
| `lint.json` | Health report in UI |
| `aegis-brain.html` | Interactive graph + reading pane |
| `okf.py serve` | Local server + Run Compile / Run Lint buttons |
| Maintain checklist | After vault edits, recompile + lint |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Graph-only brain (no markdown) | Not human-PR friendly; bad for playbooks. |
| Agent reads graph every turn | Token heavy; poor instruction quality vs Prompt Cards. |
| No graph at all | Harder to see orphans and link structure. |

---

### D6 — Single maintenance playbook for all brain mutations

#### Decision

Any add/update/ingest/restructure of durable brain knowledge **MUST** follow:

`_okf_knowledge/vault/playbooks/maintain-aegis-system.md`

Post-change checklist includes: update indexes, bidirectional cross-links, append `_okf_knowledge/log.md`, run `okf.py compile`, run `okf.py lint` (0 errors).

#### Why built this way

Without one procedure, agents:

- Drop files in the wrong zone.
- Skip `index.md` updates → orphans.
- Forget lint → broken links ship silently.

A single playbook is the **Context Node** for MAINTAIN/INGEST intent in `AGENTS.md`.

#### What it is used for

| Actor | Use |
| --- | --- |
| Agent on “add a standard” | Load playbook → decision table → write → verify |
| Human contributor | Same checklist |
| Auditors | `log.md` history of brain changes |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| “Just edit files” | Drift, orphans, schema gaps. |
| Multiple competing ingest guides | Agents pick the weakest. |

---

### D7 — Domain content is plugged in; Aegis stays generic

#### Decision

Domain knowledge (any product, monorepo, policy catalog, release process, etc.) lives **inside** the vault/standards/modules as **content**, not as the definition of Aegis.

This clean-slate package ships **no domain modules or systems** — only:

| Shipped layer | Contents |
| --- | --- |
| Protocol | `AGENTS.md` |
| House standards | `simplicity-first`, `okf-prompt-injection` (Rule #2), `metadata-headers` |
| Starter vault | `extending-aegis`, `maintain-aegis-system` |
| Kernel | lookup, Prompt Cards, lint, graph compile, serve |

**Do not remove `okf-prompt-injection.md` when sharing a thinner zip.** It is the normative home for Prompt Card injection (D4); `AGENTS.md` Path A and `okf.py lookup --card` / `okf.py card` depend on that rule remaining explicit in the vault.

Extending the framework is documented in `vault/concepts/extending-aegis.md`.

#### Why built this way

If Aegis were hard-wired to one domain, it could not host Kubernetes, Terraform, GitHub Actions, or other domains later. The control plane must stay **domain-agnostic**; domains plug in as OKF documents under `standards/` and `vault/` (Concepts, Systems, Playbooks).

#### What it is used for

| Layer | Use |
| --- | --- |
| `vault/systems/<name>.md` | System of record for a running product |
| `standards/<name>.md` | Binding house rules for that domain |
| `vault/playbooks/<name>.md` | Agent procedures |
| `vault/concepts/<name>.md` | Domain routing / patterns (replaces former Module/Vendor slots) |
| Future domains | Same slots, different files |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Hard-code one domain in AGENTS.md | Couples protocol to that domain. |
| Separate agent per domain with forked protocols | Duplicates injection/maintain rules. |
| Drop Rule #2 from the vault and “keep it only in AGENTS.md” | Loses a reviewable, lookup-able Prompt Card; agents miss the binding MUST lines. |

---

### D8 — Dual-lane future: curated vault vs AST code-index (directional)

#### Decision (intent, partially future)

| Lane | Store | Query | Inject |
| --- | --- | --- | --- |
| Ops / policy | `standards/`, `vault/playbooks/`, `concepts/` | `okf.py lookup` → `--card` | Prompt Pack |
| Code APIs | Optional generated tree e.g. `vault/code-index/` (from okf-generator-style generate) | Separate `code` lookup scope | One concept card (signature/params), not whole source files |

**Do not** merge code-index into default vault lookup or into `graph_compiler` by default.

#### Why built this way

AST generation creates **thousands** of Function/Class cards. Mixing them with dozens of Playbooks destroys lookup precision and Prompt Card quality.

Source remains untouched; generated indexes remain regenerable and disposable. Curated vault remains human-authored and small.

#### What it is used for (when wired)

| Piece | Use |
| --- | --- |
| Wrapper CLI (planned) | `lookup` vs `code` vs `gen` |
| `code-index/` | Exact symbol context for agents |
| Vault | Procedures and law |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| One flat search over vault + all symbols | Noisy, wrong defaults for Prompt Packs. |
| Replace vault with only AST dump | Loses playbooks/standards semantics. |
| READMEs beside every function in source | Pollutes product repos; conflicts with real READMEs. |

---

### D9 — Kernel Python snake_case conventions

#### Decision

- Script **filenames**: snake_case (`okf.py`, with subcommands `compile`, `lookup`, …).
- Metadata header **keys**: snake_case (`file_name`, `description`, `version`, `authors`, `intent`, `input`, `output`, `role`, `side_effects`) per `standards/metadata-headers.md`.

#### Why built this way

Consistent Python house style for agents authoring/editing kernel scripts. SCREAMING metadata keys were inconsistent with snake_case filenames and Python norms for non-constant labels in comments/docstrings.

Module-level constants (e.g. `VAULT_ROOT`) remain SCREAMING_SNAKE — that is normal Python for constants, not metadata labels.

#### What it is used for

| Surface | Use |
| --- | --- |
| File headers | Agents/humans identify script purpose quickly |
| Function docstrings | INTENT-style fields in snake_case for lint/docs consistency |
| Standard | Single reference when adding new kernel scripts |

---

### D10 — Optional future: split `AGENTS.md` into multiple specialized agents (directional)

#### Status

**Accepted as direction only.** Not implemented. The shipping control plane remains a **single** root [`AGENTS.md`](AGENTS.md). This section records *when* a split is justified and *how* it must preserve one brain and one protocol family.

#### Decision (intent, future)

Keep one package and one `_okf_knowledge/` brain. Optionally, later, expose **multiple IDE agent entrypoints** that share that brain, instead of one monolithic agent definition that always loads the full Path A/B/C contract.

| Entrypoint (example) | Loads | Primary intents | Does **not** own |
| --- | --- | --- | --- |
| `AGENTS.md` (router / default) | Pre-flight: intent → Profile → capability → handoff | All intents (thin) | Domain encyclopedias |
| `agents/generate.md` (Path A) | Generation pipeline + Prompt Pack rules + report schema A | CREATE / MODIFY / MIGRATE | Deploy reconciliation loops |
| `agents/validate.md` (Path B) | Evidence grades + review report schema | REVIEW / OPERATE / TROUBLESHOOT | Brain ingest procedures |
| `agents/execute.md` (Path C) | Reconciliation / rollback + execution plan schema | DEPLOY / UPGRADE / ROLLBACK | Architecture approval gates |
| `agents/maintain.md` | Maintain playbook binding + lint/compile checklist | MAINTAIN / INGEST | Product deploy ownership |

Names and folder layout are illustrative. Cursor/Copilot may map each file to a selectable agent; the **brain path stays** `_okf_knowledge/` adjacent to the package.

#### Why built this way (when we do it)

| Pressure | Why a split helps |
| --- | --- |
| **Context tax** | A 300+ line unified protocol competes with Prompt Cards for attention every turn |
| **Role clarity** | Operators rarely need Generation Report sections 4–6; maintainers rarely need deploy reconcile loops |
| **Safer defaults** | A generate-only agent is less likely to improvise Path C mutations |
| **IDE UX** | Users pick “Aegis Generate” vs “Aegis Maintain” instead of relying on intent detection alone |

#### Non-negotiable invariants (must hold after any split)

1. **One brain** — all agents read/write the same `_okf_knowledge/`; no per-agent fork of standards/vault.
2. **One schema** — OKF frontmatter, Prompt Cards, lookup, compile/lint remain shared (`D3`–`D6`).
3. **One precedence & budget** — knowledge precedence, evidence grades, 8-card / ~1200-token pack rules stay identical; agents must not invent divergent budgets.
4. **Single maintain playbook** — MAINTAIN/INGEST still binds to `maintain-aegis-system.md` (`D6`).
5. **Profiles** (if used later) are optional capability templates — not a Module/Vendor registry. Domain knowledge loads via OKF lookup over `standards/` + `vault/`.
6. **Router or shared preamble** — intent detection and handoff rules live in exactly one place (thin root `AGENTS.md` or `agents/_common.md`) so Path selection cannot drift.
7. **Laziness Ladder** — do not split until the unified file is proven costly; prefer Profiles + Path sections first (`D7` / Rule #1).

#### Suggested layout (when implemented)

```text
aegis-system/
├── AGENTS.md                 # thin router + shared MUST preamble (or re-export)
├── agents/                   # optional specialized entrypoints
│   ├── _common.md            # shared MUST (lookup, cards, precedence) — DRY
│   ├── generate.md           # Path A
│   ├── validate.md           # Path B
│   ├── execute.md            # Path C
│   └── maintain.md           # MAINTAIN / INGEST
├── ADR.md
├── docs/
└── _okf_knowledge/           # unchanged single brain
```

IDE install story: drop the same package folder; register multiple agents that each point at one entry file, all with working directory / vault root = package.

#### Trigger criteria (split only if most are true)

| Signal | Threshold (guidance) |
| --- | --- |
| Protocol length | Unified `AGENTS.md` regularly crowds out Prompt Pack in practice |
| Mis-routing | Agents frequently run Path A steps on Path C asks (or vice versa) |
| Team demand | Distinct roles want distinct selectable agents in the IDE |
| Maintenance cost | Editing one section regularly risks breaking unrelated paths |

If none apply, **keep the monolith** and use Profiles + intent matrix instead.

#### Migration sketch

1. Extract shared MUST block → `agents/_common.md` (lookup, cards, precedence, exit codes).  
2. Move Path A / B / C / Maintain sections into specialized files; root `AGENTS.md` becomes router + links.  
3. Update `docs/` and README install instructions for multi-agent registration.  
4. Add a lint or checklist: every specialized agent **MUST** include or reference `_common.md` invariants.  
5. Do **not** duplicate the vault; do **not** create per-agent `graph.json`.

#### What it is used for (when wired)

| Piece | Use |
| --- | --- |
| Thin `AGENTS.md` | Default agent; intent detect → hand off or load Profile |
| Specialized agent files | Smaller protocol surface per role |
| Shared brain + lookup | Same `okf.py lookup` / Prompt Cards for all entrypoints |
| Profiles | Optional templates only; not a Module/Vendor runtime gate |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Split **now** without proven pain | Violates Laziness Ladder; doubles doc sync cost |
| One agent **per Profile** only | Profiles are capability sets, not full pipeline contracts; orthogonal to Path A/B/C |
| Separate brains per agent | Divergent law, broken graph, unmaintainable |
| Copy-paste full protocol into each agent file | Drift guaranteed; contradicts D4 token discipline |
| Replace Profiles with agent split | Orthogonal concerns; Profiles remain optional templates |

#### Relationship to Profiles

| Mechanism | Answers |
| --- | --- |
| **Profile** (`kernel/profiles/`) | Optional future RBAC template (unimplemented) |
| **Agent entrypoint** (future split) | *Which* pipeline contract (generate vs validate vs execute vs maintain) is in context? |
| **OKF lookup** | *Which* standards/vault docs apply for this task? |

Prefer lookup + cards; do not assume a Module/Vendor loader.

---

## 5. How the pieces fit (runtime picture)

```text
User / IDE agent
       │
       ├─ reads AGENTS.md          (routing, Path A/B/C, §1.5 lookup rules)
       │
       ├─ okf.py lookup "<q>"      (find concept ids / paths)
       │       ├─ --card           (Prompt Pack for generation)
       │       └─ --json / pack    (machine export of cards only — D12)
       │
       ├─ optional deep read       (full playbook AFTER lookup)
       │
       ├─ generate / validate      (lint / domain gates per playbook)
       │
       └─ MAINTAIN/INGEST          (maintain-aegis-system playbook)
               ├─ edit vault/standards
               ├─ log.md
               ├─ okf.py compile → graph.json + index.json + prompt_cards.json + HTML embed
               └─ okf.py lint → lint.json
```

Visualizer path (humans):

```text
okf.py serve → aegis-brain.html → fetch/embed graph.json + lint.json
                 UI buttons → POST /api/compile | /api/lint
```

---

## 6. Consequences

### Positive

- Clear package boundary; easy distribution.
- Token-aware agent loop with an explicit find-file instruction.
- Diffable, lintable knowledge with typed documents.
- Domain content can grow without rewriting the protocol.
- Visualizer does not dictate prompt shape.

### Costs / tradeoffs

- Authors must maintain `## Prompt Card` sections on binding docs — **mechanically enforced** for `standards/*` via `okf.py lint` / CI (`DBG-308`).
- Protocol compliance for *running* lookup before generate remains **behavioral** (agents must run lookup); chat itself is not a compiler gate.
- Maintain playbook adds ceremony versus casual edits.
- Dual-lane code-index still needs a wrapper implementation to be real.

### Follow-ups (non-blocking)

1. ~~Implement `aegis-okf` wrapper: `lookup` / `pack`.~~ **Partial (D12):** `okf.py pack` + `lookup --json` land in-kernel; optional outer wrapper still open.
2. Optionally make `graph.json`/`lint.json` (and `index.json` / `prompt_cards.json`) gitignored caches with server/CLI regenerate-only — only if offline HTML story is preserved via embed.
3. ~~Add mechanical checks (hook/CI) that Prompt Cards exist on all `standards/*`.~~ **Done** — `okf.py lint` emits `DBG-308` (error) when a `standards/*` concept lacks a non-empty `## Prompt Card`; oversized cards warn as `DBG-309`. CI: `.github/workflows/okf-lint.yml`.
4. **Optional multi-agent split (D10):** only if trigger criteria fire — extract Path A/B/C/Maintain into `agents/*.md` with shared `_common.md`; keep one `_okf_knowledge/` brain. Documented in [`docs/16-multi-agent-split.md`](docs/16-multi-agent-split.md).

---

## 7. Compliance map (where the decision is binding)

| Decision | Normative / procedural home |
| --- | --- |
| D1–D3, D5 | [`AGENTS.md`](AGENTS.md) §1 |
| D4 + lookup UX | [`AGENTS.md`](AGENTS.md) Rule #1 / §1.5; [`standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md) (**keep** — Rule #2) |
| D11 knowledge plane vs corpus plane | This ADR (design record only); agent procedure in [`standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md) |
| D12 okf.py pack/tokens/secrets/ignore | This ADR; runtime in [`kernel/okf.py`](_okf_knowledge/kernel/okf.py) v1.2 |
| D6 | [`vault/playbooks/maintain-aegis-system.md`](_okf_knowledge/vault/playbooks/maintain-aegis-system.md) |
| D7 | [`vault/concepts/extending-aegis.md`](_okf_knowledge/vault/concepts/extending-aegis.md); shipped standards under [`standards/`](_okf_knowledge/standards/) |
| D8 | This ADR (directional); future wrapper + generate path |
| D9 | [`standards/metadata-headers.md`](_okf_knowledge/standards/metadata-headers.md) |
| D10 | This ADR (directional); human guide [`docs/16-multi-agent-split.md`](docs/16-multi-agent-split.md); shipping truth remains single [`AGENTS.md`](AGENTS.md) until split lands |

---

## 8. Document control

| Version | Date | Notes |
| --- | --- | --- |
| 1.6 | 2026-07-17 | D12: okf.py v1.2 — token estimate, secret scan, .okfignore, okf.config.json, pack export, lookup --json; shared assemble_prompt_pack. |
| 1.5 | 2026-07-17 | Removed unused `kernel/modules` and `kernel/vendors` slots; domain routing lives in `vault/concepts` (design: content-only, no Module/Vendor runtime). |
| 1.4 | 2026-07-17 | D11: architecture split knowledge-plane (OKF compile/lookup cache) vs corpus Grep; agent procedure stays in `okf-prompt-injection` only (ADR not a runbook). |
| 1.3 | 2026-07-14 | D10: optional future split of `AGENTS.md` into specialized agents; protocol header → v4.6.1; follow-up #4. |
| 1.2 | 2026-07-13 | Follow-up #3 done: standards Prompt Card gate in `okf.py lint` + `okf-lint` CI workflow. |
| 1.1 | 2026-07-13 | Clean-slate ADR: D7 documents empty domain slots; D2/D3 examples de-domainized; Rule #2 (`okf-prompt-injection`) called out as non-optional shipped standard. |
| 1.0 | 2026-07-13 | Initial full ADR at package root (Accepted). Aligns with protocol 4.3.1 and removal of `context.toon`. |

When this ADR changes materially, bump the table above and note it in `_okf_knowledge/log.md`.
