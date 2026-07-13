# ADR-0001: Aegis Control Plane Architecture

| Field | Value |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-07-13 |
| **Package** | `aegis-system` |
| **Protocol** | [`AGENTS.md`](AGENTS.md) v4.3.1 |
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
| 2 | `kernel/` | Execution: Python tools + Modules + Vendors |
| 3 | `standards/` | Binding MUST/SHOULD house rules |
| 4 | `vault/` | Passive memory: Concepts, Playbooks, Systems, Incidents, References |

#### Why built this way

Mixing “law,” “how-to,” “scratch,” and “scripts” in one flat folder causes:

- Agents treating drafts as standards.
- Encyclopedic product docs polluting execution modules.
- No clear ingest funnel.

Zones encode **lifecycle and authority**: inbox → curated vault/standards; kernel runs tools and domain execution docs; standards bind governance.

#### What it is used for

| Zone | Day-to-day use |
| --- | --- |
| `_inbox/` | Drop notes, logs, exports before MAINTAIN/INGEST. |
| `kernel/*.py` | `okf_lookup`, lint, graph compile, serve UI. |
| `kernel/modules|vendors` | Optional domain execution pointers (empty until you add a domain). |
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

Known types: `Concept`, `Playbook`, `System`, `Incident`, `Reference`, `Module`, `Vendor`.  
Enforced/warned by `kernel/okf_lint.py`.

#### Why built this way

Agents and tools need **machine-readable identity** without a DB:

- Lookup ranks on title/description/tags/type/path.
- Lint checks required fields and broken links.
- Graph compile builds nodes from the same metadata + body links.

Plain markdown without frontmatter forces brittle path heuristics.

#### What it is used for

| Tool / flow | Use of frontmatter |
| --- | --- |
| `okf_lookup.py` | Scoring and hit listing |
| `okf_lint.py` | Schema + health |
| `graph_compiler.py` | Node labels/types in `graph.json` |
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
   python3 _okf_knowledge/kernel/okf_lookup.py "<query>"
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
| `okf_lookup.py "prompt injection"` | Find `standards/okf-prompt-injection` etc. |
| `--paths` | Resolve filesystem path for Read tools |
| `--card` | Build Path A Prompt Pack |
| `prompt_card.py <paths>` | Extract cards when paths already known |
| Prompt Card in each standard | Durable, reviewable injection surface |

#### Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Keep `context.toon` as agent context | Recreates fat-dump tax; stale vs files. |
| Always paste full playbook | Exceeds token budget; drowns the MUST lines. |
| Embeddings / RAG | Extra infra; approximate retrieval; worse for exact standards. |

---

### D5 — `graph.json` is a visualizer/tooling artifact, not agent context

#### Decision

- `kernel/graph_compiler.py` (renamed from `toon_compiler.py`) walks the vault, builds **nodes/edges** from frontmatter + markdown links, writes `graph.json` plus slim `index.json` / `prompt_cards.json` for `okf_lookup`, and embeds into `aegis-brain.html`.
- `okf_lint.py` writes `lint.json` (also embeddable).
- `serve_vault.py` exposes `POST /api/compile` and `POST /api/lint` so the UI can regenerate without hand-editing JSON.
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
| `serve_vault.py` | Local server + Run Compile / Run Lint buttons |
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

Post-change checklist includes: update indexes, bidirectional cross-links, append `_okf_knowledge/log.md`, run `graph_compiler.py`, run `okf_lint.py` (0 errors).

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

**Do not remove `okf-prompt-injection.md` when sharing a thinner zip.** It is the normative home for Prompt Card injection (D4); `AGENTS.md` Path A and `okf_lookup.py --card` / `prompt_card.py` depend on that rule remaining explicit in the vault.

Extending the framework is documented in `vault/concepts/extending-aegis.md`.

#### Why built this way

If Aegis were hard-wired to one domain, it could not host Kubernetes, Terraform, GitHub Actions, or other domains later. The control plane must stay **domain-agnostic**; domains plug in as OKF documents + optional kernel modules/vendors.

#### What it is used for

| Layer | Use |
| --- | --- |
| `vault/systems/<name>.md` | System of record for a running product |
| `standards/<name>.md` | Binding house rules for that domain |
| `vault/playbooks/<name>.md` | Agent procedures |
| `kernel/modules/` / `kernel/vendors/` | Optional execution routing |
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
| Ops / policy | `standards/`, `vault/playbooks/`, `concepts/` | `okf_lookup.py` → `--card` | Prompt Pack |
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

- Script **filenames**: snake_case (`graph_compiler.py`, `okf_lookup.py`, …).
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

## 5. How the pieces fit (runtime picture)

```text
User / IDE agent
       │
       ├─ reads AGENTS.md          (routing, Path A/B/C, §1.5 lookup rules)
       │
       ├─ okf_lookup.py "<q>"      (find concept ids / paths)
       │       └─ --card           (Prompt Pack for generation)
       │
       ├─ optional deep read       (full playbook AFTER lookup)
       │
       ├─ generate / validate      (lint / domain gates per playbook)
       │
       └─ MAINTAIN/INGEST          (maintain-aegis-system playbook)
               ├─ edit vault/standards
               ├─ log.md
               ├─ graph_compiler.py → graph.json + index.json + prompt_cards.json + HTML embed
               └─ okf_lint.py → lint.json
```

Visualizer path (humans):

```text
serve_vault.py → aegis-brain.html → fetch/embed graph.json + lint.json
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

- Authors must maintain `## Prompt Card` sections on binding docs — **mechanically enforced** for `standards/*` via `okf_lint.py` / CI (`DBG-308`).
- Protocol compliance for *running* lookup before generate remains **behavioral** (agents must run lookup); chat itself is not a compiler gate.
- Maintain playbook adds ceremony versus casual edits.
- Dual-lane code-index still needs a wrapper implementation to be real.

### Follow-ups (non-blocking)

1. Implement `aegis-okf` (or similar) wrapper: `lookup` / `code` / `gen` / `pack`.
2. Optionally make `graph.json`/`lint.json` gitignored caches with server/CLI regenerate-only — only if offline HTML story is preserved via embed.
3. ~~Add mechanical checks (hook/CI) that Prompt Cards exist on all `standards/*`.~~ **Done** — `okf_lint.py` emits `DBG-308` (error) when a `standards/*` concept lacks a non-empty `## Prompt Card`; oversized cards warn as `DBG-309`. CI: `.github/workflows/okf-lint.yml`.

---

## 7. Compliance map (where the decision is binding)

| Decision | Normative / procedural home |
| --- | --- |
| D1–D3, D5 | [`AGENTS.md`](AGENTS.md) §1 |
| D4 + lookup UX | [`AGENTS.md`](AGENTS.md) §1.4–1.5; [`standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md) (**keep** — Rule #2) |
| D6 | [`vault/playbooks/maintain-aegis-system.md`](_okf_knowledge/vault/playbooks/maintain-aegis-system.md) |
| D7 | [`vault/concepts/extending-aegis.md`](_okf_knowledge/vault/concepts/extending-aegis.md); shipped standards under [`standards/`](_okf_knowledge/standards/) |
| D8 | This ADR (directional); future wrapper + generate path |
| D9 | [`standards/metadata-headers.md`](_okf_knowledge/standards/metadata-headers.md) |

---

## 8. Document control

| Version | Date | Notes |
| --- | --- | --- |
| 1.2 | 2026-07-13 | Follow-up #3 done: standards Prompt Card gate in `okf_lint.py` + `okf-lint` CI workflow. |
| 1.1 | 2026-07-13 | Clean-slate ADR: D7 documents empty domain slots; D2/D3 examples de-domainized; Rule #2 (`okf-prompt-injection`) called out as non-optional shipped standard. |
| 1.0 | 2026-07-13 | Initial full ADR at package root (Accepted). Aligns with protocol 4.3.1 and removal of `context.toon`. |

When this ADR changes materially, bump the table above and note it in `_okf_knowledge/log.md`.
