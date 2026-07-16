# Raw ingest — GitHub Actions YAML anchors

Source conversation: 2026-07-13 — user asked how to use GitHub workflow anchors; then INGEST THIS.

## Facts to capture

- GitHub Actions supports YAML anchors (`&`) and aliases (`*`) within a single workflow file (enabled for all repos; changelog 2025-09-18).
- Define once with `&name`, reuse with `*name` (env maps, steps lists, entire jobs).
- Same file only — no cross-workflow anchors.
- Merge keys (`<<:`) are NOT supported — exact reuse only; no base+override.
- Prefer reusable workflows / composite actions when parameterization or cross-repo sharing is needed.
- Official docs: https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#yaml-anchors-and-aliases
- Changelog: https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/

## Example patterns

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
      - run: npm test

  test:
    env: *shared_env
    runs-on: ubuntu-latest
    steps: *checkout_and_setup

  unit: &test_job
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  integration: *test_job
```

```yaml
# DOES NOT WORK on GitHub Actions
job2:
  <<: *base_job
  env:
    EXTRA: true
```

## Decision table

| Need | Use |
|------|-----|
| Same env/steps/job copied in one file | YAML anchors |
| Shared logic with inputs across repos | Reusable workflow / composite action |
| Base config + small per-job overrides | Accept duplication or factor into composite action |
