# Brain Update Log

## 2026-07-14

* **SINGLE-FILE KERNEL**: Merged all kernel scripts into one `kernel/okf.py` v1.0.0 with subcommands `lookup`, `card`, `compile`, `lint`, `enrich`, `optimize`, `scrape`, `serve` (behavior unchanged; serve now runs lint/compile in-process instead of subprocess). Old scripts removed; every doc/standard/playbook/CI/HTML reference updated to the `okf.py <subcommand>` form.
* **RETRIEVAL FIX**: `okf_lookup.py` `--card` now always emits path stubs for card-less hits instead of exiting 1 (`--all` deprecated, now default). `prompt_card.py`: card extraction now stops at level-1 headings (fixed `# Related` bleed into cards). All shipped concepts/playbooks carry a `## Prompt Card`.

* **ADR D10**: Optional future split of `AGENTS.md` into specialized agents (`agents/*.md`) sharing one brain — directional only; guide at package `docs/16-multi-agent-split.md`. ADR bumped to v1.3; protocol header aligned to v4.6.1.
* **LOOKUP**: Compile-time `index.json` + `prompt_cards.json` from `graph_compiler.py`; `okf_lookup.py` v0.2 ranks via index (fallback live vault), exact/prefix/substr weights, graph hop boost, `--type` / `--max-cards` / `--budget`.
* **GATE**: Standards Prompt Card CI/lint — `okf_lint.py` v0.4.0 errors (`DBG-308`) when `standards/*` lacks a non-empty `## Prompt Card`; warns (`DBG-309`) if card exceeds ~600 chars. Added cards to `simplicity-first` and `metadata-headers`. CI workflow: `.github/workflows/okf-lint.yml`. ADR follow-up #3 marked done (v1.2).

## 2026-07-13

* **DOCS**: Updated package-root [`README.md`](/README.md) and [`ADR.md`](/ADR.md) for clean slate — document shipped core standards (incl. Rule #2 `okf-prompt-injection`) and empty domain indexes.
* **CLEAN SLATE**: Removed trained domain content (GHA/SPVS ingest residue), emptied domain indexes, deleted `minimal-okf-prompt-cards.md`, reset compiled `graph.json` / `lint.json` / `aegis-brain.html`, and scrubbed machine-local path references for a shareable empty control plane.
