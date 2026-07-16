---
type: Concept
title: Release Manager Modes
description: release, promote, and rollback semantics for the gha-reusable-actions-workflows Release Manager.
tags: [github-actions, release-manager, concepts]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Release Manager Modes

Orchestrator: `.github/workflows/release-manager.yml` (`workflow_dispatch`).

## Inputs

| Input | Required | Notes |
| :--- | :--- | :--- |
| `component_path` | Yes | e.g. `actions/common/janitor-bot` |
| `mode` | Yes | `release` \| `promote` \| `rollback` |
| `version` | No | Release: auto-derived if empty. Promote/rollback: defaults to latest versioned tag if empty. |

## Stages

1. **Validate** — path/type, SemVer derivation (release), tag checks
2. **Security** — Conftest, Actionlint, Bandit, Shellcheck (**release only**)
3. **Execute** — tag, sync workflow file, promote/rollback stable tag

Environments: `sandbox` (release), `production` (promote/rollback).

## Mode behavior

| Mode | Security | Result |
| :--- | :--- | :--- |
| `release` | Full | Create `{safe_name}-{X.Y.Z}`; sync workflow to `.github/workflows/{name}.yml` when applicable |
| `promote` | Skipped | Point `{safe_name}-v1` at chosen versioned tag (delete+recreate, no force-push) |
| `rollback` | Skipped | Move `v1` to previous versioned tag; restore prior workflow file if needed |

## Prompt Card

```text
Release Manager (workflow_dispatch): inputs component_path, mode, version(optional).
release = versioned tag + FULL security stage (Conftest/Actionlint/Bandit/Shellcheck).
promote = move {safe_name}-v1 to chosen tag (security skipped, env production).
rollback = v1 to previous versioned tag; restore synced workflow file if needed.
```

## Related

- Concept: [SemVer from commits](/vault/concepts/semver-from-commits.md), [Component tagging](/vault/concepts/component-tagging.md)
- Playbook: [Release component](/vault/playbooks/release-gha-component.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
