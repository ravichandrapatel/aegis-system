---
type: Concept
title: GitHub Actions Domain
description: Domain routing for composite actions, reusable workflows, Release Manager, and SPVS Conftest in gha-reusable-actions-workflows.
tags: [github-actions, spvs, domain]
timestamp: 2026-07-17T03:05:00Z
status: active
---

# GitHub Actions Domain

**Triggers:** "github action", "reusable workflow", "release manager", "SPVS", "action.yml", "workflow_call", "promote tag", "conftest gha", "yaml anchor", "workflow alias"

**Minimum evidence:** component path under `actions/` or `workflows/` (or YAML in `_inbox/`) plus intent (author, review, release, promote, rollback, policy). Halt BLOCKED if unmet.

Route via Related — do not restate layout, SPVS rules, SemVer, or release semantics here.

## Prompt Card

```text
GHA domain: route to layout + gha-spvs-yaml + release-manager-modes cards.
Components under actions/{cat}/{name}/ or workflows/{cat}/{name}/ only.
Inject slim cards — never full SPVS/layout docs.
```

## Related

- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Standards: [GHA component layout](/standards/gha-component-layout.md), [GHA SPVS YAML](/standards/gha-spvs-yaml.md), [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Concepts: [SPVS Lifecycle](/vault/concepts/spvs-lifecycle.md), [Release Manager modes](/vault/concepts/release-manager-modes.md), [SemVer from commits](/vault/concepts/semver-from-commits.md), [GHA YAML Anchors](/vault/concepts/gha-yaml-anchors.md)
- Playbooks: [Author composite action](/vault/playbooks/author-gha-composite-action.md), [Release component](/vault/playbooks/release-gha-component.md)
