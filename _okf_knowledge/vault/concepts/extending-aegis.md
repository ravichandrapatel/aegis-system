---
type: Concept
title: Extending Aegis
description: How to replicate this package and grow domain knowledge without rewriting the kernel.
tags: [aegis-system, getting-started, portable, deploy]
timestamp: 2026-07-28T00:45:00Z
status: active
pack_force_when: [extend, replicate, deploy, copy-paste, portable]
---

# Extending Aegis

**Package root:** directory containing [`AGENTS.md`](/AGENTS.md) and `_okf_knowledge/`. DNA lives in AGENTS.md; this page is how to ship and grow the package.

## Replicate (copy-paste)

Copy as a unit (keep relative layout):

```
AGENTS.md
_okf_knowledge/
.cursor/rules/aegis-okf.mdc
.cursor/skills/{aegis-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,aegis-review}/
.cursor/commands/{aegis-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,aegis-review}.md
.github/skills/          # Copilot skill copies (edit alongside .cursor/skills)
.github/prompts/{aegis-discover,okf-pack,grill-me,mutation-gate,okf-writeback,okf-maintain,aegis-review}.prompt.md
.github/agents/aegis-okf.agent.md
.github/copilot-instructions.md
.github/instructions/aegis-okf.instructions.md
.github/instructions/okf-brain.instructions.md
```

Optional CI: add `.github/workflows/okf-lint.yml` that runs `okf.py compile && okf.py lint` (not shipped by default).

Place at repo root or inside one folder (e.g. `agents/`). From package root:

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

Requires Python 3.9+ (kernel is stdlib-only). Keep kernel + DNA; adapt domain cards under `standards/` and `vault/` for the target repo. Include Cursor / Copilot bindings as needed. If a parent workspace still points at legacy `knowledge/` / TOON paths, **this package’s AGENTS.md wins** when `_okf_knowledge/` is present.

## Add knowledge

1. Drop raw notes in [`_inbox/`](/_inbox/).
2. Follow [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md).

## Prompt Card

```text
Replicate: AGENTS.md + _okf_knowledge/ + Cursor (.cursor) and Copilot (.github/skills, prompts, agents, instructions).
Agent: aegis-okf. Skills/prompts: aegis-discover, okf-pack, grill-me, mutation-gate, okf-writeback, okf-maintain, aegis-review.
From package root: compile + lint. Adapt domain cards; keep kernel + DNA.
```

# Related

- [AGENTS.md](/AGENTS.md)
- [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- [Aegis Capability Discovery](/vault/concepts/aegis-capability-discovery.md)
