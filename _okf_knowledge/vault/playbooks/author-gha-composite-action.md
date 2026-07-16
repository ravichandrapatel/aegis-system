---
type: Playbook
title: Author GHA Composite Action
description: Scaffold and validate a new composite action under actions/{category}/{name}/.
tags: [github-actions, playbook, authoring]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# Trigger

You need a new composite GitHub Action in the monorepo.

# Preconditions

- Layout standard understood: [GHA component layout](/standards/gha-component-layout.md).
- Local SPVS tooling available (or use Release Manager later).

# Steps

1. Create `actions/{category}/{name}/` with `action.yml` and `readme.md`.
2. When an agent authors the action, assemble a **Prompt Pack** with `python3 _okf_knowledge/kernel/okf.py card` on layout + SPVS (+ pins) — see [OKF Prompt Injection](/standards/okf-prompt-injection.md). **MUST NOT** paste full standards.
3. Follow SPVS shell/env patterns: `set -euo pipefail`, map inputs via `env`, pin third-party `uses:` to SHA.
4. Keep `readme.md` short (inputs/outputs + one usage example).
5. Run Conftest composite scan:

```bash
conftest test --parser yaml -n composite \
  -p policies/conftest/github_actions/composite \
  -p policies/conftest/github_actions/lib \
  actions/{category}/{name}/action.yml
```

6. If Conftest fails on `CKV2_SPVS_5`, remediate with a **pin cache** (tag→SHA) rather than asking the agent to discover SHAs from scratch.
7. Run Bandit/Shellcheck on helpers if present.
8. Open PR with a ticket-prefixed conventional subject.

# Verification

- [ ] Directory matches layout standard
- [ ] Conftest composite scan passes
- [ ] `readme.md` documents inputs/outputs
- [ ] Agent prompt used a minimal card (not full SPVS dump)

## Prompt Card

```text
New composite action: actions/{category}/{name}/ with action.yml + short readme.md.
Shell: set -euo pipefail; map inputs via env (no ${{ inputs.* }} in run);
pin third-party uses: to 40-char SHA (use pin cache on CKV2_SPVS_5).
Gate: conftest test --parser yaml -n composite -p policies/conftest/github_actions/{composite,lib}.
PR subject: ticket-prefixed conventional commit.
```

# Related

- Standard: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Standard: [GHA SPVS YAML](/standards/gha-spvs-yaml.md), [GHA component layout](/standards/gha-component-layout.md)
- Concept: [GitHub Actions](/vault/concepts/github-actions.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
