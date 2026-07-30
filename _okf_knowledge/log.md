# Brain Update Log

## 2026-07-30

* **Update:** Harden round-2 — XML CDATA escape; serve allow-list (no vault GET); atomic compile writes; public lookup API; GHA SHA pins; expanded smoke tests.
* **Update:** Removed `scripts/sync-aegis-mirrors.sh`; `.github/skills` are full Copilot copies again (manual parity with `.cursor/skills`).
* **Fix:** Split `lookup.py` (search) / `pack_cmd.py` (pack + CLIs).
* **Fix:** Kernel harden pass — enrich/optimize missing imports; enrich YAML escape + LLM SSRF gate; serve loopback-only mutate APIs + bind refuse; aegis-brain XSS escapes; frontmatter block-list parse; docs aligned to `graph.json` + index v2; `tests/test_okf_smoke.py`; untracked `.okf-compile-cache.json`.
* **Dedupe pass:** Thinned discover/maintain/writeback/pack skills; collapsed DNA stubs to AGENTS pointers; capability concept → AGENTS table; cognitive-bundle Prompt Card; kernel `textutil` + import prune + rg path via `concept_id_from_path`.
* **Kernel:** `lookup` cache-miss / empty lexical hits use **ripgrep (`rg`) only** — never legacy grep; docs + Prompt Cards updated ([OKF Cognitive Bundle](vault/concepts/okf-cognitive-bundle.md), [IDE Context Guardrails](standards/ide-context-guardrails.md)).
* **Standards + concept:** Added [IDE Context Guardrails](standards/ide-context-guardrails.md) and [OKF Cognitive Bundle](vault/concepts/okf-cognitive-bundle.md); wired Copilot/Cursor instructions for no `@workspace` / pack-first.
* **Bootstrap:** Seeded portable Aegis OKF v5.1 package into `devzero-idp` from `gha-reusable-actions-workflows` scaffolding + `aegis-system` template intent. Kernel/runtime and generic OKF standards/concepts/playbooks only — no source-repo domain knowledge (GHA/SPVS) copied.
