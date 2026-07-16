---
type: Concept
title: SPVS Lifecycle
description: OWASP SPVS Plan/Integrate/Release/Operate stages mapped onto this monorepo — plus Dependency-Check runner constraints.
tags: [github-actions, spvs, lifecycle, owasp, concepts]
timestamp: 2026-07-17T03:05:00Z
status: active
---

# SPVS Lifecycle

| Stage | This repository |
| :--- | :--- |
| Plan / Develop | Commit-msg hook; ticket conventional commits; SemVer derivation |
| Integrate | Pre-commit Conftest, Actionlint, Bandit, Shellcheck (change-scoped) |
| Release | Release Manager security job; versioned tags; workflow sync |
| Operate | Promote / rollback; stable `v1` tags; branch protection / App bypass |

Branch protection, signed commits, CODEOWNERS are GitHub settings — not workflow YAML.

## Dependency-Check

When scanning with OWASP Dependency-Check: require Podman/ARC-compatible runners; no Docker-only assumptions. YAML policy itself stays in [GHA SPVS YAML](/standards/gha-spvs-yaml.md).

## Prompt Card

```text
SPVS stages: Plan=commit-msg+SemVer; Integrate=pre-commit Conftest/Actionlint/Bandit/Shellcheck;
Release=RM security+tags; Operate=promote/rollback v1.
Branch protection/CODEOWNERS = GitHub settings, not YAML.
Dependency-Check: Podman/ARC runners only — no Docker-only assumptions.
```

## Related

- Standard: [GHA SPVS YAML](/standards/gha-spvs-yaml.md)
- Concept: [GitHub Actions Domain](/vault/concepts/github-actions.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
