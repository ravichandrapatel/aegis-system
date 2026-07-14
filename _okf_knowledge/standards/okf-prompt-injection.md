---
type: Concept
title: OKF Prompt Injection
description: Binding rule — agents MUST inject slim Prompt Cards from the vault, never paste the whole brain or full standards into generation context.
tags: [standard, okf, prompting, tokens, aegis]
timestamp: 2026-07-13T16:50:00Z
status: active
---

# OKF Prompt Injection (Rule #2)

**Rule #2.** Curated OKF stays in the vault. Generation context gets **slim Prompt Cards only**.

This fixes the fat-dump tax: pasting full standards / `graph.json` / entire concept bodies into every authoring turn.

## MUST

1. Before **Artifact Generation** (Path A), assemble a **Prompt Pack** from relevant documents' `## Prompt Card` sections only.
2. Each card **MUST** target **≤150 tokens** (~600 characters). Prefer shorter.
3. Total Prompt Pack for one generation turn **SHOULD** stay **≤400 tokens** unless the user explicitly expands scope.
4. Encyclopedic bodies (full tables, citations, bench notes) **MUST** remain in the vault for lookup — **MUST NOT** be copied wholesale into the generation prompt.
5. Binding house rules for agents **MUST** expose a `## Prompt Card` section (standards especially).

## SHOULD

1. Build cards with: `python3 _okf_knowledge/kernel/okf.py card <path> [<path>...]`
2. Find paths without pasting indexes: `python3 _okf_knowledge/kernel/okf.py lookup "<query>"` then `--card` for injection.
3. Prefer one-shot validation pass over generate → fail → remediate loops when a Prompt Card already encodes the binding rules.

## FORBIDDEN

1. Pasting `_okf_knowledge/graph.json`, or full standard/concept files into the generation prompt by default.
2. Using “load the whole Aegis brain” as the default authoring strategy.
3. Treating no-OKF + multi-turn fix loops as the preferred path when a Prompt Card one-shot exists.

## Prompt Card

```text
OKF inject MUST: ## Prompt Card only (≤150 tok each); pack SHOULD ≤400 tok.
FORBIDDEN: paste graph.json/full standards into generation by default.
Build: `okf.py lookup "<q>"` then `--card` (or `okf.py card <paths>`).
```

## How to load knowledge (procedure)

| Step | Action |
| :--- | :--- |
| 1 | Route module/playbook → list 1–3 binding docs (`okf.py lookup "<intent>"`) |
| 2 | Extract each `## Prompt Card` via `okf.py card` or `okf.py lookup --card` |
| 3 | Concatenate into Prompt Pack; drop duplicates |
| 4 | Generate artifacts against the pack |
| 5 | Validate (lint / domain gates); if fail, remediate with failure text — not a fat re-dump |

## Related

- Principle: [Simplicity First](/standards/simplicity-first.md)
- Control plane: [AGENTS.md](/AGENTS.md) Path A
- Architecture ADR (package root, outside vault): `/ADR.md`
- Playbook: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Starter: [Extending Aegis](/vault/concepts/extending-aegis.md)