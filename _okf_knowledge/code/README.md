# Zone 5 — `code/` (OKF v0.2 code facts)

Externally produced `type: Code` concepts describing the host repo's artifacts
(Terraform resources, CloudFormation/Bicep templates, functions, classes,
Kubernetes manifests, Ansible plays).

**Regenerate-only.** Never hand-edit or ingest into this zone — refresh by
re-running the external producer, then `okf.py compile` + `okf.py lint`.

Schema (enforced by lint, error `DBG-310`): house frontmatter fields plus
`schema_version: 0.2`, `language`, `kind`, `source` (`relpath:line`).
Optional typed relationships (`depends_on`, `references`, `calls`,
`called_by`) become graph/adjacency edges when they resolve to concept ids.

See `AGENTS.md` §1.1, [okf-house-schema](../standards/okf-house-schema.md), and `docs/03-brain-zones.md` § Zone 5.
