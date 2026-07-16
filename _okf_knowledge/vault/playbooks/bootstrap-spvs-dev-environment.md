---
type: Playbook
title: Bootstrap SPVS Dev Environment
description: Install local hooks and scanners for gha-reusable-actions-workflows development.
tags: [github-actions, spvs, playbook, bootstrap]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Trigger

You need local commit-msg, pre-commit, Actionlint, Conftest, Bandit, and Shellcheck for this monorepo.

# Preconditions

- Clone at `/home/ghost/workspace-latest/gha-reusable-actions-workflows` (or equivalent).
- Network access to install pinned tools.

# Steps

1. `cd` to the monorepo root.
2. Run `bash policies/scripts/install_hooks.sh`.
3. Confirm `git config --global core.hooksPath` points at `~/.git-templates/hooks`.
4. Install repo pre-commit: `pre-commit install` (if not done by the installer).
5. Smoke: `pre-commit run --all-files` on a clean tree (or a small intentional change).

# Verification

- [ ] `commit-msg` rejects a subject without a ticket prefix
- [ ] `bash policies/tests/run_tests.sh` exits 0
- [ ] Actionlint/Conftest binaries resolve on PATH

## Prompt Card

```text
Bootstrap: bash policies/scripts/install_hooks.sh from monorepo root;
pre-commit install; smoke with pre-commit run --all-files.
Verify: commit-msg rejects non-ticket subjects; policies/tests/run_tests.sh exits 0.
```

# Related

- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Standard: [GHA commit subjects](/standards/gha-commit-subjects.md)
