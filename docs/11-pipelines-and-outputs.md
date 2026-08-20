# 11. Pipelines & output contracts

[← Table of contents](README.md)

After pre-flight (intent → pack → capability line → governance), OKF bifurcates into one of three paths. Non-trivial finals use the matching Markdown schema (compact or full).

> **Everything on this page is an agent output convention.** No part of the kernel produces, parses, validates, or enforces a report, a section order, a status footer, or an exit code. `okf.py` retrieves cards, compiles artifacts, and lints the vault — nothing else. Treat these shapes as the house style OKF writes in, and check them by reading, not by running a command.

**Adaptive contracts:** prefer **compact** for single-file / small / low-blast-radius work; use **full** when the **Mutation Gate** would fire, for Path C mutations (DEPLOY/UPGRADE/ROLLBACK/MAINTAIN/INGEST), user-requested full reports, or destructive risk. Gate and lifecycle: [`../AGENTS.md`](../AGENTS.md) (Change lifecycle) and the `mutation-gate` skill.

## Path A — Generation (CREATE, MODIFY, MIGRATE)

### Steps

1. Requirement collection  
2. `okf.py pack` — capability line + Prompt Cards  
3. Architecture planning (Simplicity First as the design lens)  
4. **Mutation gate** (risk-based) — hold for high-risk mutations only; wait for explicit user approval  
5. Artifact / ownership planning  
6. Artifact generation against the budgeted Prompt Pack  
7. Static validation (`okf.py lint` / domain gates)

### Output: Generation Report (convention)

Emit sections **1–3** and stop while status is `PENDING_APPROVAL`. Only after approval, emit **4–6**.

Key fields to always fill:

| Field | Meaning |
| --- | --- |
| Context Retrieved | Which cards the pack returned (or "empty pack"), plus any `related:` / `source:` edge followed afterwards |
| Context Budget Executed | `X/8` cards; note anything dropped by the budget |
| Mutation Gate Status | PENDING_APPROVAL \| APPROVED \| N/A |
| Artifact Registry | Files touched |
| Lint/Schema Results | Pass/fail/warnings from `okf.py lint` |

The lint row is the one line here backed by a real command — the rest is prose the agent is responsible for keeping honest.

## Path B — Validation (REVIEW, OPERATE, TROUBLESHOOT)

### Steps

1. Evidence collection (`provided` / `observed` / …)  
2. Evidence grading  
3. Findings vs standards from the pack  
4. Recommendations  
5. Decision: Approved | Manual Intervention | Blocked  

### Output: Architectural Review Report (convention)

Should include an Evidence Log table, a Governance & Reasoning table, a Final Decision, and Validation & Rollback commands. Evidence grades are labels the agent assigns — see [Protocol → Evidence grades](06-protocol-routing.md#evidence-grades-convention).

## Path C — Execution (DEPLOY, UPGRADE, ROLLBACK, MAINTAIN, INGEST)

### Steps

1. Execution plan (exact mutations)  
2. Prechecks  
3. Execute (CI trigger, manifests, external executor, …)  
4. Observe (`observed` evidence)  
5. Reconcile vs desired state  
6. Retry on transient failure  
7. Rollback validation on terminal failure  

For **MAINTAIN / INGEST**, the context node **MUST** be the maintain playbook:

`_okf_knowledge/vault/playbooks/maintain-okf-system.md`

### Output: Execution Plan (convention)

Include intent, context node, pre-flight checks, reconciliation loop, retry hooks, rollback path.

## Status Footer (convention, all paths)

Every report ends with:

| Field | Notes |
| --- | --- |
| **Risk Score [0–10]** | Blast radius, rollback readiness, evidence quality — agent judgement, not a computed metric |
| **Runtime State** | `READY` \| `BLOCKED` \| `PENDING_APPROVAL` (the only three `AGENTS.md` 6.0.0 defines) |
| **Exit Code** | 0 success \| 1 manual \| 2 blocked \| 3 missing inputs \| 4 unsupported — a **label**, not a process exit |
| **Governance Conflicts** | None or list |
| **Evidence Grades** | Grades encountered |

Only `READY` and `BLOCKED` ever appear in real command output, and only in the `caps:` line from `pack` / `capabilities`.

## Choosing the path quickly

| User language | Path |
| --- | --- |
| “Generate / scaffold / add Terraform…” | A |
| “Review this PR / is this safe / check against standards” | B |
| “Pods crashlooping / why is latency up” | B (operate/troubleshoot) |
| “Deploy / upgrade / rollback” | C |
| “Add this knowledge to the brain / ingest inbox” | C (MAINTAIN) |
| “Explain how X relates to Y” | Informational (no mutation); still prefer pack + structured explanation |

## Related

- [Protocol & routing](06-protocol-routing.md)
- [Maintenance](12-maintenance.md)
