---
type: Concept
title: SemVer from Commits
description: How ticket conventional commits map to SemVer bumps for component tags.
tags: [github-actions, semver, commits, concepts]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# SemVer from Commits

Implemented by `actions/common/semver` using `policies/scripts/commit_message_lib.sh`.

## Rules

1. Lookup latest tag `{safe_name}-[0-9]*`; version is the suffix.
2. No prior tag: treat current as `0.0.0` then next is **`1.0.0`**.
3. Scan commits since last tag; classify by keyword.
4. Any `feat` -> minor bump; else `fix`/`chore` -> patch; else docs/refactor/perf/test/style -> no bump.
5. Release fails if no bump-capable commits since last tag.
6. Explicit `version` input on Release Manager bypasses auto-calculation.

## Prompt Card

```text
SemVer from commits since last {safe_name}-* tag:
feat -> minor; fix/chore -> patch; docs/refactor/perf/test/style -> no bump.
No prior tag -> first release is 1.0.0. No bump-capable commits -> release FAILS.
Explicit version input bypasses auto-calculation.
```

## Related

- Standard: [GHA commit subjects](/standards/gha-commit-subjects.md)
- Concept: [Release Manager modes](/vault/concepts/release-manager-modes.md), [Component tagging](/vault/concepts/component-tagging.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
