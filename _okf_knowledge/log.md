# Brain Update Log

## 2026-07-17

* **D12 / okf.py v1.2:** Token counting (tiktoken optional), secret scan on scrape, `.okfignore` + `okf.config.json`, `pack` (md/json/xml cards-only), `lookup --json`, shared `assemble_prompt_pack`, reference compress. ADR v1.6.
* **Concept dedupe:** Deleted `vault/concepts/owasp.md` (Podman/Dependency-Check folded into `spvs-lifecycle.md`) and `vault/concepts/minimal-okf-prompt-cards.md` (pin-cache / one-shot guidance folded into `standards/okf-prompt-injection.md`). Slimmed `github-actions.md` to a domain router.
* **Removed Module/Vendor slots:** Deleted `kernel/modules/` and `kernel/vendors/` (unused by `okf.py` runtime). Relocated GHA domain routing to `vault/concepts/github-actions.md`. Updated AGENTS.md, maintain/extending indexes, ADR v1.5. Kernel walk keeps only `profiles/`.
* **Rule #2 + D11**: Agent retrieval procedure (ladder, freshness, grader access) in `standards/okf-prompt-injection.md` only. `ADR.md` D11 records the architecture split (knowledge plane vs corpus plane) — not a runbook. `AGENTS.md` Rule #1 stays a thin pointer.

## 2026-07-14

* **SINGLE-FILE KERNEL**: Merged all nine kernel scripts into one `kernel/okf.py` v1.0.0 with subcommands `lookup`, `card`, `compile`, `lint`, `enrich`, `optimize`, `scrape`, `serve` (behavior unchanged; serve now runs lint/compile in-process instead of subprocess). Old scripts removed; every doc/standard/playbook/CI/HTML reference updated to the `okf.py <subcommand>` form.
* **ENRICH**: New `kernel/okf_enrich.py` v0.1.0 (adapted from okf-generator `okf/enrich`) — LLM gap-fill limited to the three retrieval fields (`description`, `tags`, `## Prompt Card`). Stdlib-only OpenAI-compatible client (`OKF_LLM_BASE_URL` / `OKF_LLM_API_KEY` / `OKF_LLM_MODEL`), dry-run by default, idempotent gap detection, output sanitized/clamped before write, card capped at 600 chars (DBG-309).
* **RETRIEVAL FIX**: Added `## Prompt Card` to all remaining concepts, playbooks, systems, references, modules, and vendors (22/22 cards compiled) so `okf_lookup.py --card` succeeds in one shot for any query. `okf_lookup.py`: `--card` now always emits path stubs for card-less hits instead of exiting 1 (`--all` deprecated, now default). `prompt_card.py`: card extraction now stops at level-1 headings (fixed `# Related` bleed into cards).

* **ADR D10**: Optional future split of `AGENTS.md` into specialized agents (`agents/*.md`) sharing one brain — directional only; guide at package `docs/16-multi-agent-split.md`. ADR bumped to v1.3; protocol header aligned to v4.6.1.
* **LOOKUP**: Compile-time `index.json` + `prompt_cards.json` from `graph_compiler.py`; `okf_lookup.py` v0.2 ranks via index (fallback live vault), exact/prefix/substr weights, graph hop boost, `--type` / `--max-cards` / `--budget`.
* **GATE**: Standards Prompt Card CI/lint — `okf_lint.py` v0.4.0 errors (`DBG-308`) when `standards/*` lacks a non-empty `## Prompt Card`; warns (`DBG-309`) if card exceeds ~600 chars. Added cards to `simplicity-first` and `metadata-headers`. CI workflow: `.github/workflows/okf-lint.yml`. ADR follow-up #3 marked done (v1.2).

## 2026-07-13

* **DOCS**: Updated package-root [`README.md`](/README.md) and [`ADR.md`](/ADR.md) for clean slate — document shipped core standards (incl. Rule #2 `okf-prompt-injection`) and empty domain indexes.
* **CLEAN SLATE**: Removed trained domain content (GHA/SPVS ingest residue), emptied domain indexes, deleted `minimal-okf-prompt-cards.md`, reset compiled `graph.json` / `lint.json` / `aegis-brain.html`, and scrubbed machine-local path references for a shareable empty control plane.
