# Brain Update Log

## 2026-07-14

* **ADR D10**: Optional future split of `AGENTS.md` into specialized agents (`agents/*.md`) sharing one brain — directional only; guide at package `docs/16-multi-agent-split.md`. ADR bumped to v1.3; protocol header aligned to v4.6.1.
* **LOOKUP**: Compile-time `index.json` + `prompt_cards.json` from `graph_compiler.py`; `okf_lookup.py` v0.2 ranks via index (fallback live vault), exact/prefix/substr weights, graph hop boost, `--type` / `--max-cards` / `--budget`.
* **GATE**: Standards Prompt Card CI/lint — `okf_lint.py` v0.4.0 errors (`DBG-308`) when `standards/*` lacks a non-empty `## Prompt Card`; warns (`DBG-309`) if card exceeds ~600 chars. Added cards to `simplicity-first` and `metadata-headers`. CI workflow: `.github/workflows/okf-lint.yml`. ADR follow-up #3 marked done (v1.2).

## 2026-07-13

* **DOCS**: Updated package-root [`README.md`](/README.md) and [`ADR.md`](/ADR.md) for clean slate — document shipped core standards (incl. Rule #2 `okf-prompt-injection`) and empty domain indexes.
* **CLEAN SLATE**: Removed trained domain content (GHA/SPVS ingest residue), emptied domain indexes, deleted `minimal-okf-prompt-cards.md`, reset compiled `graph.json` / `lint.json` / `aegis-brain.html`, and scrubbed machine-local path references for a shareable empty control plane.
