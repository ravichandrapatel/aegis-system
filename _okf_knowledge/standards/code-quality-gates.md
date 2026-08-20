---
type: Concept
title: Code Quality Gates
description: Machine-checkable quality and security gates per DevOps stack, so review spends itself on judgement.
tags: [standard, code-quality, gates, ci, security, devops, iac]
generated: { by: okf-agent/cursor, at: 2026-08-21T02:45:00Z }
status: stable
pack_force_when: [quality gate, ci gate, terraform review, kubernetes review, dockerfile review, workflow hardening, shift left]
---

# Code Quality Gates

**Binding** for changes to infrastructure, pipelines, containers, and runtime code. Anything a machine can decide **MUST** be decided by a machine before a human opens the diff — reviewer attention is the scarce resource, and [Code Review](/standards/code-review.md) spends it on design, blast radius, and intent.

## The ladder

Run cheapest-first; a rung that fails stops the change.

| Rung | Gate | Blocks merge |
| --- | --- | --- |
| 1 | Format (`fmt`, formatter) | yes |
| 2 | Lint / static analysis | yes |
| 3 | Secret scan (whole diff, incl. `.tfvars`, `values.yaml`) | yes |
| 4 | Security & policy scan | yes on high/critical |
| 5 | Tests (unit → integration) | yes |
| 6 | Change preview evidence (`plan`, `diff`, dry-run) attached to the PR | yes for infra |
| 7 | Coverage / complexity trend | warn |

**MUST**: every gate runs in CI as a required status check, not only on a developer's laptop.
**MUST**: gate output is attached to the change, so the reviewer reads evidence rather than re-deriving it.
**FORBIDDEN**: waving a red gate through with a comment; either fix it or record an explicit, time-boxed exception in the PR.

## Universal review invariants

- **No secrets in the repo** — no keys, tokens, passwords, or `.env` content in code, IaC, manifests, logs, or test fixtures.
- **Least privilege** — every identity, role, token, and security group grants the minimum that works.
- **Pinned dependencies** — no floating tags on anything that executes in your pipeline.
- **Reversible** — a documented rollback, or an explicit statement that the change is irreversible.
- **Idempotent** — re-running the change converges instead of drifting or duplicating.

## Per-stack checks

### Terraform / IaC

- `terraform fmt -check` and `validate` clean; `checkov` or `trivy config` gate on high/critical.
- **`plan` output attached to the PR.** Review the plan, not just the HCL — scan for `-/+` replacements and any destroy the author did not intend.
- Provider and module versions pinned; remote state encrypted and locked.
- `lifecycle { prevent_destroy = true }` on stateful resources (databases, caches, buckets).
- No `0.0.0.0/0` on sensitive ports; encryption at rest enabled; public access blocked by default.
- Documented state moves whenever a resource address changed.

### Kubernetes / Helm

- Resource `requests`/`limits` set; probes defined; replicas and `PodDisruptionBudget` sane for the tier.
- `securityContext`: non-root, read-only root filesystem, dropped capabilities; no privileged pods.
- RBAC scoped to a namespace — no cluster-admin bindings without an owner decision.
- Image pinned by digest or immutable tag, never `:latest`.
- Secrets from a manager (External Secrets / Vault / CSI), never inline base64.

### Containers

- Minimal, pinned base image; multi-stage build; non-root `USER`.
- No secrets in build args or layers; `.dockerignore` excludes credentials and `.git`.
- Image scan gates on high/critical; SBOM produced for anything shipped.

### GitHub Actions / CI

- `permissions: {}` at workflow level; each job grants only the scopes it needs.
- Third-party actions pinned to a **40-character commit SHA** with the version in a trailing comment; Dependabot enabled for the `github-actions` ecosystem.
- `pull_request_target`, `workflow_run`, and `issue_comment` treated as privileged — **never** check out and execute untrusted fork code in them.
- Untrusted input (`github.event.*`, `inputs.*`) mapped to `env:` before use in `run:` — never interpolated straight into a shell line.
- OIDC federation for cloud auth instead of long-lived keys, with the trust policy pinned to repo *and* ref.
- `CODEOWNERS` covers `.github/workflows/`.

### Shell

- `set -euo pipefail` at the top of every `run:` block; no `set -x` in anything that touches secrets.
- All variable expansions double-quoted; `mktemp` for temp files; traps clean up.

### Python / Go

- Python: type hints, `ruff`/`mypy` clean, no `eval`/`exec`, no `subprocess(..., shell=True)`, pinned requirements. House rules: [Python Naming](/standards/python-naming.md), [Metadata Headers](/standards/metadata-headers.md).
- Go: `go vet` and `staticcheck` clean, errors wrapped and handled, contexts propagated, structured logging.

## Prompt Card

```text
Gate what a machine can decide before a human reads the diff: fmt → lint → secret scan → policy scan → tests → change preview (plan/diff), each a required CI check. Never wave a red gate through.
Invariants: no secrets, least privilege, pinned deps, documented rollback, idempotent.
Terraform: attach plan, watch -/+ destroys, pin providers, prevent_destroy on stateful. K8s: limits, probes, non-root, no :latest, RBAC scoped. Actions: permissions:{}, 40-char SHA pins, untrusted input via env:, OIDC not static keys. Shell: set -euo pipefail, quote everything.
```

# Related

- Judgement: [Code Review](/standards/code-review.md)
- Simplicity: [Simplicity First](/standards/simplicity-first.md)
- Python house rules: [Python Naming](/standards/python-naming.md) · [Metadata Headers](/standards/metadata-headers.md)
