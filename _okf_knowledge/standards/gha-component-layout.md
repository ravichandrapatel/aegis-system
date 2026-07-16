---
type: Concept
title: GHA Component Layout
description: Required directory contract for composite actions and reusable workflows in the monorepo.
tags: [standard, github-actions, layout, monorepo]
timestamp: 2026-07-13T16:00:00Z
status: active
---

# GHA Component Layout

## MUST

1. Composite actions **MUST** live at `actions/{category}/{name}/`.
2. Each action directory **MUST** contain `action.yml` (or `action.yaml`) and `readme.md`.
3. Reusable workflows **MUST** live at `workflows/{category}/{name}/`.
4. Each workflow directory **MUST** contain exactly one `workflow.yml` (or `.yaml`) and `readme.md`.
5. Release Manager `component_path` **MUST** start with `actions/` or `workflows/`.
6. Categories in use today: `common`, `security` (actions); `common` (workflows).

## FORBIDDEN

1. Inventing alternate trees outside `actions/` or `workflows/` for publishable components.
2. Multiple workflow YAML files in one workflow component directory.

## Prompt Card

```text
Layout MUST:
- actions/{category}/{name}/ → action.yml|yaml + readme.md
- workflows/{category}/{name}/ → exactly one workflow.yml|yaml + readme.md
- component_path starts with actions/ or workflows/
- categories today: actions common|security; workflows common
FORBIDDEN: trees outside actions|workflows; multi workflow YAML per dir
```

## Related

- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Concept: [GitHub Actions](/vault/concepts/github-actions.md)
- Playbook: [Author composite action](/vault/playbooks/author-gha-composite-action.md)
- Standard: [Simplicity First](/standards/simplicity-first.md), [OKF Prompt Injection](/standards/okf-prompt-injection.md)
