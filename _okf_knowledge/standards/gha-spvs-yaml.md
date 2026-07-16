---
type: Concept
title: GHA SPVS YAML
description: OWASP SPVS Conftest policy catalog for workflow and composite action YAML (MUST pass, no soft-fail).
tags: [standard, github-actions, spvs, conftest, security]
timestamp: 2026-07-13T16:00:00Z
status: active
---

# GHA SPVS YAML

Policies live under `policies/conftest/github_actions/`. Scan with Conftest namespaces `-n workflow` or `-n composite`. Findings **MUST** fail the scan.

## Permissions (MUST)

| ID | Rule |
| :--- | :--- |
| CKV2_SPVS_1 | Every job **MUST** declare `permissions:` |
| CKV2_SPVS_8 | OIDC cloud login jobs **MUST** have `id-token: write` |
| CKV2_SPVS_9 | Workflow-level permissions **MUST** be declared; **MUST NOT** grant write on contents/packages/id-token/security-events/deployments at workflow root |
| CKV2_SPVS_10 | **MUST NOT** use `write-all` |
| CKV2_SPVS_11 | `contents: write` jobs **MUST** set `environment:` |
| CKV2_SPVS_15 | **MUST NOT** use `pull_request_target` |
| CKV2_SPVS_12 | **MUST NOT** use bare `runs-on: self-hosted` |
| CKV2_GHA_1 | Top-level permissions **MUST NOT** be `write-all` |

## Supply chain and shell (MUST)

| ID | Rule |
| :--- | :--- |
| CKV2_SPVS_2 | Bash `run:` **MUST** include `set -euo pipefail` |
| CKV2_SPVS_3 | **MUST NOT** enable xtrace |
| CKV2_SPVS_4 | Python invocations **MUST** use `-u` or `PYTHONUNBUFFERED=1` |
| CKV2_SPVS_5 | Third-party `uses:` **MUST** pin to 40-char SHA, `./`, `docker://`, or approved internal `/actions/` tags |
| CKV2_SPVS_5B | Local `uses:` **MUST NOT** start with `../` |
| CKV2_SPVS_6 | `${{ inputs.* }}` **MUST NOT** appear in `run:` strings — map via `env:` |
| CKV2_SPVS_13 | **MUST NOT** use curl\|bash style installers |
| CKV2_SPVS_7 | **MUST NOT** set static cloud credential env vars |
| CKV_GHA_1–4 | No unsecure commands; no user-controlled context in `run:`; no suspicious curl/nc patterns |

## Policy skips (MUST)

When `SPVS_SKIP_POLICY` is set, `SPVS_SKIP_REASON` **MUST** also be set (non-empty) at the same scope. `CKV2_SPVS_5` and `CKV2_SPVS_5B` are paired skips.

## Prompt Card

```text
SPVS MUST (workflow/composite):
- every job: permissions: (workflows)
- bash run: set -euo pipefail; no set -x
- no ${{ inputs.* }} in run — map via env
- uses: 40-char SHA | ./ | docker:// | /actions/ tag; no ../
- no write-all; no pull_request_target; no bare self-hosted
- no curl|bash; no AWS_ACCESS_KEY_ID/SECRET/SESSION static env
- contents:write jobs need environment:
```

## Related

- Concept: [SPVS lifecycle](/vault/concepts/spvs-lifecycle.md)
- Standard: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Playbook: [Run local policy tests](/vault/playbooks/run-gha-local-policy-tests.md)
