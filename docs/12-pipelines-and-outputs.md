# 12. Pipelines & output contracts

[← Table of contents](README.md)

After pre-flight (intent → profile → capability → context → governance), Aegis bifurcates into one of three paths. **Final answers MUST use the matching Markdown schema** and end with the **Status Footer**. Unstructured chat as the sole deliverable is non-conformant.

Binding templates: [`../AGENTS.md`](../AGENTS.md) §5.

## Path A — Generation (CREATE, MODIFY, MIGRATE)

### Steps

1. Requirement collection  
2. Architecture planning (`simplicity-first`)  
3. **Approval gate** — HALT; wait for explicit user approval  
4. Artifact registry / ownership planning  
5. Contract generation (inputs/outputs/metadata)  
6. Artifact generation against budgeted Prompt Pack  
7. Static validation (`okf_lint.py` / domain gates)

### Output: Generation Report

Emit sections **1–3** and stop while status is **PENDING**. Only after approval, emit **4–6**.

Key fields to always fill:

| Field | Meaning |
| --- | --- |
| Profile Loaded | Which `kernel/profiles/*` applied |
| Graph Traversal Path | e.g. EKS → IRSA → IAM → OIDC |
| Context Budget Executed | `X/8` cards; note evictions |
| Approval Gate Status | PENDING \| APPROVED |
| Artifact Registry | Files + owning module paths |
| Lint/Schema Results | Pass/fail/warnings |

## Path B — Validation (REVIEW, OPERATE, TROUBLESHOOT)

### Steps

1. Evidence collection (`provided` / `observed` / …)  
2. Evidence grading  
3. Findings vs standards / profile  
4. Recommendations  
5. Decision: Approved | Manual Intervention | Blocked  

### Output: Architectural Review Report

Must include Evidence Log table, Governance & Reasoning table, Final Decision, Validation & Rollback commands.

## Path C — Execution (DEPLOY, UPGRADE, ROLLBACK, MAINTAIN, INGEST)

### Steps

1. Execution plan (exact mutations)  
2. Prechecks  
3. Execute (CI trigger, manifests, external executor, …)  
4. Observe (`observed` evidence)  
5. Reconcile vs desired state  
6. Retry on transient failure  
7. Rollback validation on terminal failure  

For **MAINTAIN / INGEST**, Context Node **MUST** be the maintain playbook:

`_okf_knowledge/vault/playbooks/maintain-aegis-system.md`

### Output: Execution Plan

Include intent, profile, context node, pre-flight checks, reconciliation loop, retry hooks, rollback path.

## Status Footer (all paths)

Every report ends with:

| Field | Notes |
| --- | --- |
| **Risk Score [0–10]** | Blast radius, rollback readiness, evidence quality |
| **Exit Code** | 0 success \| 1 manual \| 2 blocked \| 3 missing inputs \| 4 unsupported |
| **Governance Conflicts** | None or list |
| **Graph Depth Traversed** | Integer |
| **Evidence Grades** | Grades encountered |

## Choosing the path quickly

| User language | Path |
| --- | --- |
| “Generate / scaffold / add Terraform…” | A |
| “Review this PR / is this safe / check against standards” | B |
| “Pods crashlooping / why is latency up” | B (operate/troubleshoot) |
| “Deploy / upgrade / rollback” | C |
| “Add this knowledge to the brain / ingest inbox” | C (MAINTAIN) |
| “Explain how X relates to Y” | Informational (no mutation); still prefer lookup + structured explanation |

## Related

- [Protocol & routing](06-protocol-routing.md)
- [Maintenance](13-maintenance.md)
- [Profiles](07-profiles.md)
