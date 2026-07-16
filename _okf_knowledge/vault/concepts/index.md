# Vault: Concepts

Core definitions and architectural patterns live here.
Every file is `type: Concept`.

| Title | Description |
| :--- | :--- |
| [Component Tagging](component-tagging.md) | safe_name derivation and versioned vs stable tag conventions for GHA components. |
| [Extending Aegis](extending-aegis.md) | How to grow this empty framework with your own standards and vault knowledge. |
| [GitHub Actions](github-actions.md) | Domain routing for composite actions, reusable workflows, Release Manager, and SPVS Conftest. |
| [GHA YAML Anchors](gha-yaml-anchors.md) | Reuse env, steps, or jobs inside one GitHub Actions workflow with YAML anchors (&) and aliases (*) — no merge keys. |
| [Release Manager Modes](release-manager-modes.md) | release, promote, and rollback semantics for the gha-reusable-actions-workflows Release Manager. |
| [SemVer from Commits](semver-from-commits.md) | How ticket conventional commits map to SemVer bumps for component tags. |
| [SPVS Lifecycle](spvs-lifecycle.md) | OWASP SPVS stages mapped onto this monorepo, plus Dependency-Check runner constraints. |
