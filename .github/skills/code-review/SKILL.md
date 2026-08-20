---
name: code-review
description: >-
  Review a diff, branch, or PR against the code-review bar and DevOps quality gates.
  Use for "review my PR/changes", pre-merge checks, IaC/pipeline/container audits, or code-quality questions.
---

<!-- GENERATED FILE — do not edit.
     Source: .cursor/skills/code-review/SKILL.md
     Regenerate: python3 tools/sync_skills.py -->
Review; do not silently rewrite the author's change. Fix only what the user asked you to fix.

## How to run

1. Pack — the `caps:` header confirms the environment, so there is no separate discovery step:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "code review quality gates <stack keywords>"
```

2. **Scope the change.** Never review from memory of the repo — read the actual diff.

```bash
git diff --stat main...HEAD && git diff main...HEAD   # local branch
gh pr view <n> --json title,body,files && gh pr diff <n>   # GitHub PR
```

If the diff exceeds ~400 changed lines, say so first and propose a split before reviewing line by line.

3. **Run the gates before reading code** ([`code-quality-gates.md`](../../../_okf_knowledge/standards/code-quality-gates.md)): format → lint → secret scan → security/policy scan → tests → change preview. Report what you ran and what you could not run; a gate you skipped is not a gate that passed.
4. **Review top-down** ([`code-review.md`](../../../_okf_knowledge/standards/code-review.md)): design → blast radius/rollback → functionality → security → complexity → tests → naming → style → docs → observability/cost. Route by what changed:

| Changed paths | Focus |
| --- | --- |
| `*.tf`, `*.tfvars` | `plan` attached, `-/+` destroys, pinned providers, `prevent_destroy`, IAM scope, open CIDRs |
| `*.yaml` (k8s), `charts/` | limits/probes, non-root `securityContext`, RBAC scope, pinned image digest, secret source |
| `Dockerfile` | pinned base, multi-stage, non-root `USER`, no secrets in layers |
| `.github/workflows/` | `permissions: {}`, 40-char SHA pins, privileged triggers, untrusted input via `env:`, OIDC |
| `*.sh`, `run:` blocks | `set -euo pipefail`, quoted expansions, no `set -x` near secrets |
| `*.py`, `*.go` | house naming/headers, error paths, no `shell=True`/`eval`, tests |

5. **Write findings as Conventional Comments** — `label (decorations): subject` + why. Non-blocking unless `(blocking)`. Each finding cites `file:line` and the standard it comes from. Leave at least one sincere `praise`.
6. **Decide:** **Approved** | **Manual Intervention** | **Blocked**.

## Posting to GitHub

Only when the user asks. Draft first, show the body, then:

```bash
gh pr review <n> --comment --body-file review.md          # findings, no verdict
gh pr review <n> --request-changes --body-file review.md  # blocking findings
```

Confirm the active account (`gh auth status`) before writing to any remote.

## Output (compact)

```markdown
### Code Review: [target] (N files, ±M lines)
**Gates** fmt ✓ · lint ✓ · secrets ✓ · policy ⚠ 2 high · tests ✗ not run
**Decision** Approved | Manual Intervention | Blocked

issue (security,blocking): <subject> — `path:line`
<why + suggested fix>

nitpick: <subject> — `path:line`
praise: <subject>
```

## Guardrails

- Approve on **code health improved**, not on perfection. Do not block on taste — the linter owns style.
- Never invent a violation: no `file:line` and no standard means it is a `question`, not an `issue`.
- Pre-existing debt outside the diff → `note` + follow-up, never a blocker.
- Do not read or echo `.env`, keys, or tokens; report the path and the exposure only.
- Applying a high-risk fix (IAM, secrets, prod, destructive) → `mutation-gate` first.
- Durable finding worth keeping → `okf-writeback`.
