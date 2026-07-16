# Standards — The Law

House rules live here under `standards/`. They override references, upstream docs, and agent memory. Every file is `type: Concept` with tag `standard`.

# Principles

* [Simplicity First (Rule #1)](simplicity-first.md) — The Laziness Ladder: simplest, shortest, minimal solution that works.
* [OKF Prompt Injection (Rule #2)](okf-prompt-injection.md) — Slim Prompt Cards only; never paste the whole brain.

# Code Quality

* [Metadata Headers](metadata-headers.md) — Required file/function/class metadata blocks for all new code.

# Domain (GHA / SPVS)

* [GHA Commit Subjects](gha-commit-subjects.md) — Ticket-prefixed conventional commit subjects required for hooks and SemVer bumps.
* [GHA Component Layout](gha-component-layout.md) — Required directory contract for composite actions and reusable workflows in the monorepo.
* [GHA SPVS YAML](gha-spvs-yaml.md) — OWASP SPVS Conftest policy catalog for workflow and composite action YAML (MUST pass, no soft-fail).
