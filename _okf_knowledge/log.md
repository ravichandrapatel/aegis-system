# Brain Update Log

## 2026-07-30

* **Dedupe pass:** Thinned discover/maintain/writeback/pack skills; `.cursor/skills` canonical + `scripts/sync-aegis-mirrors.sh`; collapsed DNA stubs to AGENTS pointers; capability concept → AGENTS table; cognitive-bundle Prompt Card; kernel `textutil` + import prune + rg path via `concept_id_from_path`.
* **Kernel:** `lookup` cache-miss / empty lexical hits use **ripgrep (`rg`) only** — never legacy grep; docs + Prompt Cards updated ([OKF Cognitive Bundle](vault/concepts/okf-cognitive-bundle.md), [IDE Context Guardrails](standards/ide-context-guardrails.md)).
* **Standards + concept:** Added [IDE Context Guardrails](standards/ide-context-guardrails.md) and [OKF Cognitive Bundle](vault/concepts/okf-cognitive-bundle.md); wired Copilot/Cursor instructions for no `@workspace` / pack-first.
* **Bootstrap:** Seeded portable Aegis OKF v5.1 package into `devzero-idp` from `gha-reusable-actions-workflows` scaffolding + `aegis-system` template intent. Kernel/runtime and generic OKF standards/concepts/playbooks only — no source-repo domain knowledge (GHA/SPVS) copied.
