---
type: Playbook
title: Release GHA Component
description: Run Release Manager mode release/promote/rollback for a monorepo component.
tags: [github-actions, playbook, release]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Trigger

You need to release, promote, or roll back a composite action or reusable workflow.

# Preconditions

- Component path valid under `actions/` or `workflows/`.
- Secrets `RELEASE_APP_ID` and `RELEASE_APP_PRIVATE_KEY` configured.
- Understand [Release Manager modes](/vault/concepts/release-manager-modes.md).

# Steps

1. Ensure commits since last tag include `feat`/`fix`/`chore` if auto-bumping ([SemVer from commits](/vault/concepts/semver-from-commits.md)).
2. Open Actions -> **Release Manager** (`workflow_dispatch`).
3. Set `component_path` (e.g. `actions/common/janitor-bot`).
4. Set `mode`:
   - `release` — sandbox versioned tag + security stage
   - `promote` — move `{safe_name}-v1` to chosen version
   - `rollback` — previous versioned tag (+ restore workflow file if needed)
5. Optionally set `version` to pin SemVer / target.
6. Wait for Validate -> Security (release only) -> Execute.

# Verification

- [ ] Versioned or stable tag exists remotely as expected ([Component tagging](/vault/concepts/component-tagging.md))
- [ ] For workflow releases, `.github/workflows/{name}.yml` matches source
- [ ] Consumers can reference `@v1` after promote

## Prompt Card

```text
Release: Actions -> Release Manager (workflow_dispatch); set component_path + mode
(release|promote|rollback), optional version. Auto-bump needs feat/fix/chore commits
since last tag. Verify remote tag ({safe_name}-{X.Y.Z} or -v1) and synced workflow file.
```

# Related

- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Concept: [Release Manager modes](/vault/concepts/release-manager-modes.md)
- Standard: [GHA commit subjects](/standards/gha-commit-subjects.md)
