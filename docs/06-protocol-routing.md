# 6. Protocol & routing

[← Table of contents](README.md)

Binding source: [`../AGENTS.md`](../AGENTS.md) (version `6.0.0` in the file header). Normative keywords follow RFC 2119 (**MUST**, **SHOULD**, …).

> **What is enforced, and what is not.** Only two things in this page are executed by code: the capability probe and the pack budget. Everything else — precedence, evidence grades, report shapes, exit codes, runtime states — is an **agent output convention**. `okf.py` never reads a report, never validates a footer, and never halts an agent. Sections below are marked accordingly.

## Persona & mission (short)

OKF never guesses. It maps requirements against the local brain, pulls related concepts via link-derived graph proximity, mandates a **Mutation Gate** where risk warrants, and verifies against local standards. Absolute bar: **Zero Downtime, Zero Surprises.**

## Intent → pipeline matrix

| Intent | Lifecycle phase | Active pipeline | Core objective |
| --- | --- | --- | --- |
| **CREATE** / **MODIFY** / **MIGRATE** | Discover, Design, Generate | **Generation (Path A)** | Pack → plan → edit → report the delta |
| **REVIEW** | Review | **Validation (Path B)** | Compare artifacts to standards |
| **OPERATE** / **TROUBLESHOOT** | Operate, Recover | **Validation (Path B)** | Analyze observations, metrics, logs |
| **DEPLOY** / **UPGRADE** | Deploy, Upgrade | **Execution (Path C)** | Sequential application / reconciliation |
| **ROLLBACK** | Recover | **Execution (Path C)** | Explicit reversion steps |
| **MAINTAIN** / **INGEST** | Operate | **Execution (Path C)** | Mutate brain via maintain playbook |
| **EXPLAIN** / **COMPARE** | Discover, Design | **Informational** | Map relationships; no state change |

If the user’s ask is ambiguous, detect intent first — do not skip into generation.

## Pre-flight (every non-trivial request)

```
[Intent Detection]
        → [okf.py pack "<keywords>"]   ← capability line + Prompt Cards, one command
        → [Read caps: READY | BLOCKED]
        → [Governance / Mutation Gate]
        → Path A | Path B | Path C
```

Capability discovery is **folded into retrieval**. Rule #1 is one command, not two:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"
```

Mermaid diagram + step explanations: [Overview — End-to-end flow](01-overview.md#end-to-end-flow-when-a-user-asks-for-something).

### Capability check (enforced by code)

`okf.py capabilities` — or the `caps:` line that `pack` prints for free — probes eight things and reports a single runtime hint.

```
caps: READY | all present | features: rung1_inbox,advisory_explain,prompt_pack,vault_lookup,okf_compile,okf_lint,rung2_maintain,git_ops,okf_v02
```

| Probed capability | `present` means |
| --- | --- |
| `python` | The interpreter running the probe |
| `filesystem` | Repo root exists and is readable |
| `shell` | `$SHELL`, `bash`, or `sh` available |
| `brain` | `kernel/okf.py` + `vault/` + `standards/` exist (`degraded` when `graph.json` is missing — run `compile`) |
| `yaml` | PyYAML is importable, so OKF v0.2 nested frontmatter parses (`degraded` when missing; adds the `okf_v02` feature when present) |
| `git` | `git` on PATH (`degraded` when there is no `.git` in the repo root) |
| `compile` / `lint` | `okf.py` subcommands are runnable |

| Runtime hint | When | Exit code |
| --- | --- | --- |
| `READY` | Baseline (python/filesystem/shell) and `brain` present | `0` |
| `BLOCKED` | Any baseline capability or `brain` missing | `0`, or **`4`** with `--strict` |

There is no "required modules / vendors" registry — those directories do not exist. `BLOCKED` on a non-trivial create/modify means the agent stops and says so; that halt is behavioral, not a process exit.

Use `--no-caps` on `pack` when you want the cards alone (scripting, diffing packs).

### Context expansion & budget (enforced by code)

Build the Prompt Pack with `okf.py pack` or `lookup --card`. Hop-boost reads adjacency from `kernel/src/graph.json`; the same adjacency is printed under each selected card as a `related:` line so the agent can expand by **traversing an edge** instead of re-querying. **Do not** paste compiled artifacts into the generation prompt.

| Budget rule | Value | Flag |
| --- | --- | --- |
| Max Prompt Cards | **8** | `--max-cards` |
| Token budget | **~1200** | `--budget` |
| Relevance floor | **24** (`0` disables) | `--min-score` |

**How assembly actually works** — there is no priority-tier eviction:

1. Concepts whose `pack_force_when` matches the query (on token boundaries) are collected first.
2. Ranked lookup hits are appended, deduplicated by concept id.
3. Anything scoring below `--min-score` is dropped.
4. Cards are added **in that rank order** until either 8 cards or the token budget is reached, then assembly stops.
5. If the very first card alone exceeds the budget, it is **truncated** (with a marker) rather than blowing the budget.
6. **After** selection, each card gets its `trust:` / `source:` / `related:` footer — attached last, so traversal never displaces a card and never breaks `--budget`. Cap: 3 links per card (`related_links` in `kernel/src/config.py`; `0` disables).

Tokens are counted with `tiktoken` (`cl100k_base`) when the optional package is installed, otherwise with a word/punctuation heuristic.

**An empty pack is a valid answer.** `pack` always exits `0`; zero cards means the vault has nothing binding on the topic. Proceed on general engineering judgement and capture anything durable to `_inbox/` — do not re-query variations hunting for a hit. To browse instead of searching, enter at `_okf_knowledge/index.md` and follow its links.

**Need more than the cards hold? Traverse.** Follow a `related:` or `source:` path from a card you already have; re-running `pack` with reworded queries is the reflex this footer exists to replace. Detail: [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md#traversal-following-the-graph).

### Graph edges (convention — kernel edges are untyped)

> **Agent output convention.** `okf.py compile` emits **untyped** `{source, target}` edges derived from markdown cross-links, and `pack` prints them as bare paths on the `related:` line — nothing more. The semantics below are how agents are expected to *reason* about relationships; no code reads, validates, or halts on an edge type.

| Edge | Meaning | Example |
| --- | --- | --- |
| `depends_on` | Strict structural requirement | EKS → VPC |
| `implements` | Execution relationship | Terraform → AWS |
| `governed_by` | Policy enforcement | System → Standard |
| `references` | Contextual linkage | Incident → Playbook |
| `compatible_with` | Treated as a hard gate by the agent; missing/violated → the agent stops | Version constraints |
| `supersedes` | Prefer the newer node | B supersedes A |

The `compatible_with` HALT is a reasoning rule the agent applies. Nothing in the kernel detects or enforces it.

## Knowledge precedence (convention)

> **Agent output convention — no kernel enforcement.** Lookup ranks by lexical score and graph proximity only. It does not know that a standard outranks a vault note; the agent applies that ordering.

When sources conflict, resolve in this order:

1. Local Brain **standards** (via pack / Prompt Cards)
2. Local workspace (`_inbox/`, terminal context)
3. Passive **vault**
4. Official external metadata (OCI / Git APIs)

**Fail-closed:** at plan time the standard wins and the agent notes the correction; at execution time a conflict with the approved plan stops the work (`PENDING_APPROVAL` or `BLOCKED`) instead of being guessed. There is no `owns` / `priority` frontmatter arbitration — those fields do not exist in the schema.

## Evidence grades (convention)

> **Agent output convention — no kernel enforcement.** Nothing computes or validates a grade; these are labels the agent attaches to what it cites.

| Grade | Meaning | High-risk work |
| --- | --- | --- |
| `verified` | Cryptographically signed / official OCI/Git source of truth | Preferred |
| `observed` | Runtime via API/CLI | Preferred for operate/deploy |
| `provided` | User-supplied manifests/logs | High trust, unverified |
| `inferred` | Ecosystem defaults | Use carefully |
| `assumed` | Unsupported | **Prohibited** for production claims |

## Runtime states (convention, partly emitted)

| State | Meaning | Emitted by kernel? |
| --- | --- | --- |
| `READY` | Proceed | **Yes** — `caps:` line / `capabilities` |
| `BLOCKED` | Missing capability or unresolved conflict | **Yes** — `caps:` line / `capabilities` |
| `PENDING_APPROVAL` | Mutation Gate held, waiting on the user | No — agent label only |

`AGENTS.md` 6.0.0 defines exactly these three.

## Vault retrieval rule (Rule #1 — Pack First)

Before grepping randomly or pasting large docs:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<query>"
```

1. **MUST** pack (or `lookup --card`) when the path is unknown — once per task, not once per message.
2. **MUST NOT** paste whole vault files or compiled artifacts into generation by default.
3. Trivial work (typo, rename, one known-path question) skips the pack entirely.

Details: [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md).

## Exit codes

### Kernel exit codes (real)

| Command | Code | Meaning |
| --- | ---: | --- |
| `pack` | 0 | Always — including an empty pack |
| `lookup` | 0 / 1 | Hits / no hits |
| `card` | 0 / 1 | Cards emitted / a file or card was missing |
| `lint` | 0 / 1 | No errors / errors found (warnings still exit 0) |
| `compile` | 0 / 1 | Wrote artifacts / OSError while writing |
| `capabilities` | 0 / 4 | Always 0 unless `--strict` and `BLOCKED` |

### Report exit codes (convention)

> **Agent output convention — no kernel enforcement.** These are labels an agent puts in a report footer. No process returns them.

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 1 | Manual intervention / unresolved conflict |
| 2 | Blocked |
| 3 | Missing inputs |
| 4 | Unsupported (capability gap) |

## Related

- [Pipelines & outputs](11-pipelines-and-outputs.md)
- [Compiled artifacts](07-compiled-artifacts.md)
