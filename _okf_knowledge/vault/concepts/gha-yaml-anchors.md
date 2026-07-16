---
type: Concept
title: GHA YAML Anchors
description: Reuse env, steps, or jobs inside one GitHub Actions workflow with YAML anchors (&) and aliases (*) — no merge keys.
tags: [github-actions, yaml, anchors, workflow, reuse]
timestamp: 2026-07-14T17:40:00Z
status: active
---

# GHA YAML Anchors

GitHub Actions supports YAML **anchors** (`&`) and **aliases** (`*`) to copy configuration within a **single** workflow file. Enabled for all repositories (Sep 2025).

## Syntax

| Mark | Role |
| :--- | :--- |
| `&name` | Define an anchor on first use |
| `*name` | Insert an exact copy of that node |

```yaml
jobs:
  build:
    env: &shared_env
      NODE_ENV: production
      CI: true
    steps: &checkout_and_setup
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci

  test:
    env: *shared_env
    runs-on: ubuntu-latest
    steps: *checkout_and_setup
```

Reuse an entire job:

```yaml
jobs:
  unit: &test_job
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  integration: *test_job
```

## Constraints (MUST know)

| Rule | Detail |
| :--- | :--- |
| Same file only | Anchors do **not** cross workflow files |
| Exact copy only | Alias is a full duplicate of the anchored node |
| No merge keys | `<<:` is **not** supported — no base + override |

```yaml
# FORBIDDEN on GitHub Actions — merge keys do not work
job2:
  <<: *base_job
  env:
    EXTRA: true
```

## When to use what

| Need | Use |
| :--- | :--- |
| Same env / steps / job repeated in one file | YAML anchors |
| Parameterized or cross-repo shared logic | Reusable workflow (`workflow_call`) or composite action |
| Base job + small per-job diffs | Keep duplication, or extract shared steps into a composite action |

Prefer the simplest rung: if duplication is tiny, skip anchors ([Simplicity First](/standards/simplicity-first.md)).

## Prompt Card

```text
YAML anchors (&) / aliases (*) reuse nodes within ONE workflow file only.
Alias = exact copy; merge keys (<<:) FORBIDDEN on GitHub Actions.
Cross-file or parameterized reuse -> reusable workflow / composite action.
Tiny duplication? Skip anchors (Simplicity First).
```

## Related

- Concept: [GitHub Actions](/vault/concepts/github-actions.md)
- System: [gha-reusable-actions-workflows](/vault/systems/gha-reusable-actions-workflows.md)
- Standard: [GHA component layout](/standards/gha-component-layout.md)

# Citations

1. [Reusing workflow configurations — YAML anchors and aliases](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#yaml-anchors-and-aliases)
2. [Changelog: Actions YAML anchors (2025-09-18)](https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/)
