# 6. Protocol & routing

[← Table of contents](README.md)

Binding source: [`../AGENTS.md`](../AGENTS.md) (v4.6.1). Normative keywords follow RFC 2119 (**MUST**, **SHOULD**, …).

## Persona & mission (short)

Aegis never guesses. It maps requirements against the local brain, resolves dependencies via **typed graph traversal**, mandates **approval gates** where required, and verifies against local standards. Absolute bar: **Zero Downtime, Zero Surprises.**

## Intent → pipeline matrix

| Intent | Lifecycle phase | Active pipeline | Core objective |
| --- | --- | --- | --- |
| **CREATE** / **MODIFY** | Discover, Design, Generate | **Generation (Path A)** | Requirements → graph → code/delta |
| **REVIEW** | Review | **Validation (Path B)** | Compare artifacts to standards |
| **OPERATE** / **TROUBLESHOOT** | Operate, Recover | **Validation (Path B)** | Analyze observations, metrics, logs |
| **DEPLOY** / **UPGRADE** | Deploy, Upgrade | **Execution (Path C)** | Sequential application / reconciliation |
| **ROLLBACK** | Recover | **Execution (Path C)** | Explicit reversion steps |
| **MAINTAIN** / **INGEST** | Operate | **Execution (Path C)** | Mutate brain via maintain playbook |
| **EXPLAIN** / **COMPARE** | Discover, Design | **Informational** | Map relationships; no state change |

If the user’s ask is ambiguous, detect intent first — do not skip into generation.

## Pre-flight state machine (every request)

```
[Intent Detection]
        → [Load Profile (kernel/profiles/)]
        → [Capability Check]
        → [Context Expansion (Typed Graph Traversal)]
        → [Governance Engine]
        → Path A | Path B | Path C
```

### Capability Registry Check (§4.1)

Before planning or traversing, verify the loaded Profile’s required modules, vendors, and standards exist locally.

| Result | Exit |
| --- | --- |
| Required capability **missing** | **HALT** — Exit Code `4` (Unsupported) |
| Present | Continue to context expansion |

### Context expansion & budget (§4.2)

Build a Context / Prompt Pack by traversing `graph.json` (and using lookup for cards). **Do not** paste `graph.json` into the generation prompt.

| Budget rule | Value |
| --- | --- |
| Max Prompt Cards (normative) | **8** |
| Max tokens (advisory) | **~1200** |

**Deterministic eviction** when over budget (apply in order):

1. Priority tier: Standards > Modules > Vendors > Playbooks > References  
2. Graph distance (fewer hops from target wins)  
3. Higher frontmatter `priority`  
4. Newer `last_modified`

Drop lowest-ranking cards until ≤ 8 cards remain.

### Recognized edge types (typed traversal)

| Edge | Meaning | Example |
| --- | --- | --- |
| `depends_on` | Strict structural requirement | EKS → VPC |
| `implements` | Execution relationship | Terraform → AWS |
| `governed_by` | Policy enforcement | Module → Standard |
| `references` | Contextual linkage | Incident → Playbook |
| `compatible_with` | Hard gate; missing/violated → **HALT** | Version constraints |
| `supersedes` | Evict older node; replace with newer | B supersedes A |

> Implementation note: today’s `okf.py compile` primarily emits link-derived edges for the visualizer. Model richer typed edges in document bodies/frontmatter as the graph schema evolves; protocol already defines the semantics agents must respect.

## Knowledge precedence (§2.2)

When sources conflict, resolve in this order:

1. Local Brain **standards** (via lookup / Prompt Cards)  
2. Local workspace (`_inbox/`, terminal context)  
3. **Vendors**  
4. **Modules**  
5. Passive **vault**  
6. Official external metadata (OCI / Git APIs)

**Owns / priority:** overlapping standards or modules → document whose `owns` claims the domain wins; if both claim it, higher `priority` wins.  
**Fail-closed:** same `owns` + same `priority` → conflict error, **HALT** exit `1`, no guessing.

## Evidence grades (§2.1)

| Grade | Meaning | Production Profiles |
| --- | --- | --- |
| `verified` | Cryptographically signed / official OCI/Git SoT | Preferred |
| `observed` | Runtime via API/CLI | Preferred for operate/deploy |
| `provided` | User-supplied manifests/logs | High trust, unverified |
| `inferred` | Ecosystem defaults | Use carefully |
| `assumed` | Unsupported | **Prohibited** in production profiles |

## Vault lookup rule (§1.5)

Before grepping randomly or pasting large docs:

```bash
python3 _okf_knowledge/kernel/okf.py lookup "<query>"
```

1. **MUST** lookup when the path is unknown.  
2. **MUST NOT** paste whole vault files into generation by default — use `--card` / Prompt Pack.

Details: [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md).

## Exit codes (status footer)

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 1 | Manual intervention / unresolved conflict |
| 2 | Blocked |
| 3 | Missing inputs |
| 4 | Unsupported (capability / profile gap) |

## Related

- [Pipelines & outputs](12-pipelines-and-outputs.md)
- [Profiles](07-profiles.md)
- [Compiled artifacts](08-compiled-artifacts.md)
