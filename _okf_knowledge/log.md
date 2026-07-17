# Brain Update Log

## 2026-07-18

* **KERNEL v1.4 (steal from hermes-okf, Aegis-shaped):** `list`, `show` (`--raw`/`--card`), `log-append` (ephemeral chronology), `doctor` (setup diagnostics), `snapshot`/`restore` under `.okf-snapshots/` (gitignored). No Hermes plugin/SDK, no open `Decision`/`Session` taxonomy — durable knowledge still via maintain playbook. Maintain playbook subcommand table updated.
* **RETRIEVAL QUALITY (content, no AGENTS.md churn):** Narrowed `okf-house-schema` `pack_force_when` to `[frontmatter]` (dropped `maintain`/`ingest`/`schema`; hyphenated force keys never match tokenized queries). Gave `maintain-aegis-system` `pack_force_when: [maintain, ingest, write-back, inbox]` + richer tags/description/card; aligned write-back inbox rule with no every-turn sweep. Synced `okf-prompt-injection` pack budget to ≤8 cards / ≈1200 tok. Added `## Prompt Card` to `kernel/profiles/_schema`.
* **DOCS:** Stopped linking architecture notes from README/docs/vault; architecture record is private to maintainers.
* **CLEAN SLATE (domain wipe):** Removed all `gha-reusable-actions-workflows` / SPVS domain content from the empty control plane — standards (`gha-*`), concepts, playbooks, system card, pin-cache/readme references, and archived inbox residue. Indexes emptied to framework-only (simplicity-first, okf-prompt-injection, metadata-headers, extending-aegis, maintain-aegis-system). Scrubbed GHA examples from `okf-prompt-injection.md`, profile schema, maintain playbook, and `.github/agents/aegis.agent.md`. Recompile + relint required so `aegis-brain.html` embeds match.

## 2026-07-17

* **D12 / okf.py v1.2:** Token counting (tiktoken optional), secret scan on scrape, `.okfignore` + `okf.config.json`, `pack` (md/json/xml cards-only), `lookup --json`, shared `assemble_prompt_pack`, reference compress. architecture notes v1.6.
* **Concept dedupe:** Deleted `vault/concepts/owasp.md` (Podman/Dependency-Check folded into `spvs-lifecycle.md`) and `vault/concepts/minimal-okf-prompt-cards.md` (pin-cache / one-shot guidance folded into `standards/okf-prompt-injection.md`). Slimmed `github-actions.md` to a domain router.
* **Removed Module/Vendor slots:** Deleted `kernel/modules/` and `kernel/vendors/` (unused by `okf.py` runtime). Relocated GHA domain routing to `vault/concepts/github-actions.md`. Updated AGENTS.md, maintain/extending indexes, architecture notes v1.5. Kernel walk keeps only `profiles/`.
* **Rule #2 + D11**: Agent retrieval procedure (ladder, freshness, grader access) in `standards/okf-prompt-injection.md` only. architecture notes (D11) records the architecture split (knowledge plane vs corpus plane) — not a runbook. `AGENTS.md` Rule #1 stays a thin pointer.

## 2026-07-14

* **SINGLE-FILE KERNEL**: Merged all nine kernel scripts into one `kernel/okf.py` v1.0.0 with subcommands `lookup`, `card`, `compile`, `lint`, `enrich`, `optimize`, `scrape`, `serve` (behavior unchanged; serve now runs lint/compile in-process instead of subprocess). Old scripts removed; every doc/standard/playbook/CI/HTML reference updated to the `okf.py <subcommand>` form.
* **ENRICH**: New `kernel/okf_enrich.py` v0.1.0 (adapted from okf-generator `okf/enrich`) — LLM gap-fill limited to the three retrieval fields (`description`, `tags`, `## Prompt Card`). Stdlib-only OpenAI-compatible client (`OKF_LLM_BASE_URL` / `OKF_LLM_API_KEY` / `OKF_LLM_MODEL`), dry-run by default, idempotent gap detection, output sanitized/clamped before write, card capped at 600 chars (DBG-309).
* **RETRIEVAL FIX**: Added `## Prompt Card` to all remaining concepts, playbooks, systems, references, modules, and vendors (22/22 cards compiled) so `okf_lookup.py --card` succeeds in one shot for any query. `okf_lookup.py`: `--card` now always emits path stubs for card-less hits instead of exiting 1 (`--all` deprecated, now default). `prompt_card.py`: card extraction now stops at level-1 headings (fixed `# Related` bleed into cards).

* **Multi-agent split (D10)**: Optional future split of `AGENTS.md` into specialized agents (`agents/*.md`) sharing one brain — directional only; guide at package `docs/16-multi-agent-split.md`. architecture notes bumped to v1.3; protocol header aligned to v4.6.1.
* **LOOKUP**: Compile-time `index.json` + `prompt_cards.json` from `graph_compiler.py`; `okf_lookup.py` v0.2 ranks via index (fallback live vault), exact/prefix/substr weights, graph hop boost, `--type` / `--max-cards` / `--budget`.
* **GATE**: Standards Prompt Card CI/lint — `okf_lint.py` v0.4.0 errors (`DBG-308`) when `standards/*` lacks a non-empty `## Prompt Card`; warns (`DBG-309`) if card exceeds ~600 chars. Added cards to `simplicity-first` and `metadata-headers`. CI workflow: `.github/workflows/okf-lint.yml`. Architecture follow-up #3 marked done (v1.2).

## 2026-07-13

* **DOCS**: Updated package-root [`README.md`](/README.md) and architecture notes for clean slate — document shipped core standards (incl. Rule #2 `okf-prompt-injection`) and empty domain indexes.
* **CLEAN SLATE**: Removed trained domain content (GHA/SPVS ingest residue), emptied domain indexes, deleted `minimal-okf-prompt-cards.md`, reset compiled `graph.json` / `lint.json` / `aegis-brain.html`, and scrubbed machine-local path references for a shareable empty control plane.

## 2026-07-17T17:33:33Z

- Updated `standards/gha-spvs-yaml.md` Prompt Card + CKV2_SPVS_5: clarify that GitHub `actions/*` (e.g. checkout@v4) MUST use 40-char SHA; monorepo `actions/cat/name@tag` ≠ github.com owner `actions`.

## 2026-07-17T19:00:00Z

- **SELF-LEARN / INGEST FIX** (`AGENTS.md` v4.8.0): §1.3 schema corrected from `last_modified` to the kernel-canonical `timestamp` field (kernel `enrich`/`optimize`/recency ranking never read `last_modified`, so agent-authored files broke cache invalidation and tie-breaking); `kernel/profiles/_schema.md` aligned. New binding §1.6 Self-Learning Loop: five write-back triggers, capture-vs-full-ingest ladder, mandatory `_inbox/` sweep in PRE-FLIGHT and Write-Back Check in POST-FLIGHT. Path C now maps MAINTAIN/INGEST stages concretely onto the maintain playbook (Observe = compile+lint, Reconcile = 0 errors). Playbook Trigger updated to include §1.6 self-learn.

## 2026-07-17T19:05:00Z

- **KERNEL v1.3 / ARTIFACT SLIM**: Dropped visualizer stack — no more `graph.json`, `lint.json`, `aegis-brain.html`, or `okf.py serve`. Compile now writes only `index.json` v3 (entries + inverted + adjacency for hop-boost) and `prompt_cards.json`. Lint is stdout-only. Embedded `DEFAULT_OKF_CONFIG` in `kernel/okf.py` (deleted `okf.config.json`). Docs: maintain playbook, brain `index.md`, `AGENTS.md` §1.4.

## 2026-07-17T19:10:00Z

- **VISUALIZER EMBED-ONLY**: Restored `aegis-brain.html` + `okf.py serve`. Graph/lint payloads embed into HTML script tags (`graph-data` / `lint-data`); still no `graph.json` / `lint.json` / `okf.config.json` sidecars. Lookup keeps `index.json` v3 + `prompt_cards.json`. Kernel v1.3.1.

## 2026-07-17T19:20:00Z

- **PROMPT CARD EXCEPTIONS**: `prompt_card_max_chars` frontmatter overrides DBG-309 / enrich clamp (hard ceiling 2000). `pack_force_when` catalogs force-include first and bypass pack `max_cards` + token budget (safety cap 4). Wired on `standards/gha-spvs-yaml.md`; pin-cache already had `pack_force_when`. Docs: okf-prompt-injection, maintain playbook, AGENTS.md §1.3.

## 2026-07-17T20:30:00Z

- **ZONE 5 / OKF v0.2 CODE CONCEPTS** (`AGENTS.md` v4.8.0 §1.1/§1.3/§2.2/§4.2/§1.6): new `code/` zone for externally produced `type: Code` concepts (regenerate-only). Kernel: `Code` in taxonomy; lint `DBG-310` (missing `schema_version`/`language`/`kind`/`source`) + `DBG-311` (version mismatch); orphan-check exemption; typed-relationship frontmatter (`depends_on`/`references`/`calls`/`called_by`) → graph/adjacency edges; pack assembly ranks `Code` below all curated types; `enrich` skips `Code`. Placeholder `code/README.md`. Docs 02/03/04/05/09/10 + DNA aligned.

## 2026-07-17T20:45:00Z

- **DOC DEDUP / DRIFT SWEEP**: `last_modified` → `timestamp` in docs 05/06/07 (kernel `_schema.md` already canonical); protocol version refs 4.6.x → 4.8.0 (docs 02/06/README); removed stale `graph.json`/`lint.json` sidecar references across docs 01/02/06/08/09/10/11/14/15 and `standards/okf-prompt-injection.md` (timestamp bumped; embed-only since kernel v1.3.1); retired `Module`/`Vendor` type rows and `kernel/modules|vendors/` paths in docs 03/04/05/07/13/15 (AGENTS.md §4.1 — no Module/Vendor registry); ADR D10 operational tables slimmed to a pointer at `docs/16-multi-agent-split.md` (was a drifting near-duplicate).

## 2026-07-17T21:00:00Z

- **BOOTLOADER SLIM** (`AGENTS.md` v4.9.0, ~140 lines): protocol cut to mission + Rule #1 + zone stubs + intent matrix + path one-liners + compressed output contracts. Full schema relocated to new standard `standards/okf-house-schema.md` (`owns: [frontmatter, schema, document-types]`, `pack_force_when: [frontmatter, schema, ingest, maintain]`). Self-learning write-back trigger/ladder detail relocated into `vault/playbooks/maintain-aegis-system.md` § Self-learning write-back. Kernel `known_types()` prefers house-schema type table, then AGENTS.md fallback, then seed. DNA bumped to v4.9.0; docs version refs → 4.9.0; schema-detail pointers retargeted to house-schema. ADR Document control 1.8 (D13).

## 2026-07-17T21:15:00Z

- **PROTOCOL POLISH v4.9.1** (AGENTS.md + DNA lockstep): positive governance framing (no "IGNORE Copilot"); adaptive compact/full output contracts (Path C mutations full-only); RFC-2119 diet — MUST/MUST NOT reserved for true invariants. Docs version refs → 4.9.1; docs/12 adaptive note; ADR Document control 1.9 (D14).

## 2026-07-17T21:20:00Z

- **REMOVED Copilot DNA:** deleted `.github/agents/aegis.agent.md` (and empty `agents/` dir). Single protocol is root `AGENTS.md` for all IDEs. Updated README, docs/02, docs/14 install paths; maintain playbook trigger no longer mentions agent bridge.

## 2026-07-17T21:30:00Z

- **KERNEL STABILIZE v4.9.2:** Rule #1 = Prompt Pack invariant (CLI is default implementation); inbox only on write-back or MAINTAIN/INGEST (no every-turn sweep); Approval Gate → risk-based **Mutation Gate**; pack budget ≤8 cards hard, target ≈1200 tokens. Docs synced; ADR 1.10 (D15). Freeze major architecture — next gains from OKF content quality.

## 2026-07-17T21:25:06Z — Observation

v1.4 smoke — doctor/list/show/snapshot
