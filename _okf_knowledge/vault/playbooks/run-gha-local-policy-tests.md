---
type: Playbook
title: Run GHA Local Policy Tests
description: Execute Conftest verify/scan and policy unit tests for the monorepo.
tags: [github-actions, playbook, conftest, testing]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Trigger

You changed Rego policies, action/workflow YAML, or need a full local SPVS gate.

# Preconditions

- Conftest installed (see [Bootstrap SPVS Dev Environment](/vault/playbooks/bootstrap-spvs-dev-environment.md)).
- Working tree at monorepo root.

# Steps

1. Full suite: `bash policies/tests/run_tests.sh`
2. Single workflow:

```bash
conftest test --parser yaml -n workflow \
  -p policies/conftest/github_actions/workflow \
  -p policies/conftest/github_actions/lib \
  path/to/workflow.yml
```

3. Single composite action:

```bash
conftest test --parser yaml -n composite \
  -p policies/conftest/github_actions/composite \
  -p policies/conftest/github_actions/lib \
  path/to/action.yml
```

4. If `policies/conftest/` changed, run `pre-commit run --all-files` (full rescan path).

# Verification

- [ ] `run_tests.sh` exits 0
- [ ] No open SPVS findings without paired `SPVS_SKIP_POLICY` + `SPVS_SKIP_REASON`

## Prompt Card

```text
Full gate: bash policies/tests/run_tests.sh (exit 0 required).
Single file: conftest test --parser yaml -n workflow|composite
  -p policies/conftest/github_actions/{workflow|composite} -p .../lib <file>.
Rego changed? pre-commit run --all-files. Skips need SPVS_SKIP_POLICY + SPVS_SKIP_REASON.
```

# Related

- Standard: [GHA SPVS YAML](/standards/gha-spvs-yaml.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
