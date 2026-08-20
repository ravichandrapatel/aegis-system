---
type: Concept
title: Extending OKF
description: How to replicate this package and grow domain knowledge without rewriting the kernel.
tags: [okf-system, getting-started, portable]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: [extend okf, replicate okf, copy-paste, portable package]
---

# Extending OKF

**Package root:** directory containing [`AGENTS.md`](/AGENTS.md) and `_okf_knowledge/`. DNA lives in AGENTS.md; this page is how to ship and grow the package.

## Replicate (copy-paste)

Copy as a unit (keep relative layout):

```
AGENTS.md
_okf_knowledge/
tools/sync_skills.py
.cursor/rules/okf.mdc
.cursor/skills/{okf-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,okf-review,code-review}/
.cursor/commands/{okf-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,okf-review,code-review}.md
.github/skills/          # GENERATED — never edit by hand
.github/prompts/{okf-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,okf-review,code-review}.prompt.md
.github/agents/okf.agent.md
.github/copilot-instructions.md
.github/instructions/okf-brain.instructions.md
```

`.cursor/skills/` is the single source of truth. Regenerate the Copilot copies with `python3 tools/sync_skills.py`; CI enforces it with `--check`.

Optional CI: `.github/workflows/okf-lint.yml` runs compile, lint, the skill drift check, and the kernel tests.

Place at repo root or inside one folder (e.g. `agents/`). From package root:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

Requires Python 3.9+ (kernel is stdlib-only). Keep kernel + DNA; adapt domain cards under `standards/` and `vault/` for the target repo. Include Cursor / Copilot bindings as needed. If a parent workspace still points at legacy `knowledge/` / TOON paths, **this package’s AGENTS.md wins** when `_okf_knowledge/` is present.

## Add knowledge

1. Drop raw notes in [`_inbox/`](/_inbox/).
2. Follow [Maintain OKF System](/vault/playbooks/maintain-okf-system.md).

A vault holding only OKF's own documentation makes Rule #1 pure overhead: every pack costs a command and returns nothing task-relevant. Fill `standards/` and `vault/` with the domain knowledge the target repo actually argues about — pinned versions, deployment runbooks, house policy — or expect empty packs and answer from general judgement.

## Prompt Card

```text
Replicate: AGENTS.md + _okf_knowledge/ + tools/sync_skills.py + Cursor (.cursor) and Copilot (.github).
.cursor/skills is the source of truth; .github/skills is generated (tools/sync_skills.py).
From package root: compile + lint. Keep kernel + DNA; fill standards/ and vault/ with DOMAIN
knowledge — a self-referential vault makes every pack empty and Rule #1 pure cost.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [OKF Runtime CLI](/vault/systems/okf-runtime.md)
- [Maintain OKF System](/vault/playbooks/maintain-okf-system.md)
- [OKF Capability Discovery](/vault/concepts/okf-capability-discovery.md)
