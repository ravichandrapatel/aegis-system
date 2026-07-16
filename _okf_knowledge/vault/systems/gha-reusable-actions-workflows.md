---
type: System
title: gha-reusable-actions-workflows
description: Monorepo for reusable GitHub Actions, reusable workflows, SPVS Conftest policies, and Release Manager lifecycle.
tags: [github-actions, spvs, release-manager, monorepo, system]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# gha-reusable-actions-workflows

Workspace path: `/home/ghost/workspace-latest/gha-reusable-actions-workflows`

Monorepo that publishes composite GitHub Actions and reusable workflows under an OWASP SPVS-aligned release plane (Validate -> Security -> Execute).

## Directory map

| Path | Role |
| :--- | :--- |
| `actions/{category}/{name}/` | Composite actions (`action.yml` + `readme.md` required) |
| `workflows/{category}/{name}/` | Reusable workflows (one `workflow.yml` + `readme.md`) |
| `policies/conftest/github_actions/` | Conftest Rego (namespaces `workflow` / `composite`) |
| `policies/scripts/` | Commit-msg lib, hook installer, Conftest runners |
| `.github/workflows/` | Release Manager + synced published workflows |
| `.pre-commit-config.yaml` | Local Shellcheck, Bandit, Actionlint, SPVS Conftest |

## Components (current clone)

| Kind | Path |
| :--- | :--- |
| Action | `actions/common/semver` |
| Action | `actions/common/drift-auditor` |
| Action | `actions/common/git-path-filter` |
| Action | `actions/common/issues-bot` |
| Action | `actions/common/janitor-bot` |
| Action | `actions/common/prbot` |
| Action | `actions/security/owasp-dependency-check` |
| Workflow | `workflows/common/dummy-workflow` |
| Orchestrator | `.github/workflows/release-manager.yml` |

## Release plane

Modes: `release` (sandbox versioned tag), `promote` (stable `{name}-v1`), `rollback` (previous versioned tag).

Tag patterns: `{safe_name}-{X.Y.Z}` and `{safe_name}-v1`.

Security Stage 2 (release only): Conftest SPVS, Actionlint (workflows), Bandit (`*.py`), Shellcheck (`*.sh`).

## Prerequisites

- GitHub App secrets: `RELEASE_APP_ID`, `RELEASE_APP_PRIVATE_KEY` (`contents: write`, `workflows: write`)
- Branch protection bypass for the App when syncing workflows to `main`

## Prompt Card

```text
Monorepo: actions/{cat}/{name}/ (action.yml+readme.md); workflows/{cat}/{name}/
(workflow.yml+readme.md); Rego in policies/conftest/github_actions/.
Release plane: release -> promote -> rollback; tags {safe_name}-{X.Y.Z} / -v1.
Needs GitHub App secrets RELEASE_APP_ID / RELEASE_APP_PRIVATE_KEY.
```

## Related

- Concept: [GitHub Actions](/vault/concepts/github-actions.md)
- Standards: [GHA commit subjects](/standards/gha-commit-subjects.md), [GHA SPVS YAML](/standards/gha-spvs-yaml.md), [GHA component layout](/standards/gha-component-layout.md), [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Concepts: [Release Manager modes](/vault/concepts/release-manager-modes.md), [SemVer from commits](/vault/concepts/semver-from-commits.md), [SPVS lifecycle](/vault/concepts/spvs-lifecycle.md), [GHA YAML Anchors](/vault/concepts/gha-yaml-anchors.md)
- Playbooks: [Release component](/vault/playbooks/release-gha-component.md), [Bootstrap SPVS env](/vault/playbooks/bootstrap-spvs-dev-environment.md)
- Reference: [Repo README](/vault/references/gha-reusable-readme.md)
