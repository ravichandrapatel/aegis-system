# A/B Benchmark — OKF vs no-OKF

> **Purpose**
>
> Benchmark whether the Aegis/OKF knowledge system improves engineering outcomes over a baseline model by running two isolated subagents on the same task using the same model.

Copy this file into a Cursor chat (or `@`-mention it), fill every `{{...}}` placeholder, then send.

The parent agent **orchestrates only**. It must **not** implement the task itself.
If a parent-run gate fails, the parent **must** feed the failure back to that arm for fixes and re-score true cost-to-PASS (never treat a draft FAIL as final without the fix loop).

**HTML report must use the checked-in template** — do not hand-author a new layout:

- Template: [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html)
- Renderer: [`render_bench_report.py`](render_bench_report.py)

**Aegis is not automatic for subagents.** The OKF arm must be told to use Aegis; the no-OKF arm must be told not to.

**Compliance knowledge isolation (hard):** Org compliance and the **answer-key sources for this task’s `{{PARENT_GATE}}`** MUST NOT appear in the shared task brief or either arm’s initial prompt. The OKF arm obtains compliance **only** via live `okf.py lookup` / `okf.py card` Prompt Cards (dynamic per domain — see AGENTS.md Rule #1). Fill `{{GATE_ANSWER_KEY_GLOBS}}` with the grader paths for **this** gate only (GHA example: `**/policies/**`, `**/*.rego`). Do not put a universal path ban into AGENTS.md. Parent runs `{{PARENT_GATE}}` and an isolation audit against those globs.

---

```text
# A/B Benchmark — OKF vs no-OKF (parent orchestrator only)

You are the parent. Do **not** implement the task.

## Parent Responsibilities

- Do **not** implement the task.
- Launch **two parallel subagents** (same model).
- Verify outputs independently (re-run {{PARENT_GATE}} yourself).
- **Never put {{PARENT_GATE}}, SPVS, Conftest, Rego paths, or SHA-pin rules into the baseline arm’s initial prompt.**
- **If the parent gate fails for either arm: feed the failure output back to that arm and make it fix the issues** (do not score a draft FAIL as final).
- Re-verify after each fix loop until PASS or remediation budget is exhausted.
- Score **true cost-to-PASS** (initial + all remediation loops).
- Produce a standalone HTML benchmark report from BENCH_REPORT_TEMPLATE.html.

## Knowledge isolation (mandatory)

| Source | OKF arm | Baseline arm | Parent |
| --- | --- | --- | --- |
| Shared `{{TASK_DESCRIPTION}}` | Functional only | Functional only | — |
| Aegis / OKF Prompt Cards (live lookup) | **Required** (only compliance source) | Forbidden | — |
| `{{GATE_ANSWER_KEY_GLOBS}}` (grader for this gate) | **Forbidden** | **Forbidden** | May read to run gate |
| Pins/versions/catalogs | From **cards** only | Public knowledge only | — |
| `{{PARENT_GATE}}` | Not in initial prompt | **Not in initial prompt** | Runs for score |
| Gate failure stdout on resume | Allowed (fix loop) | Allowed (fix loop) | Pastes raw output |

`{{GATE_ANSWER_KEY_GLOBS}}` is **per task / per gate** — not a global AGENTS.md list. Example for the sample GHA Conftest gate: `**/policies/**`, `**/*.rego`, Conftest policy dirs used by `{{PARENT_GATE}}`. For another domain, name that domain’s grader paths instead.

Shared task text and both initial arm prompts MUST be free of org-compliance text and those answer-key paths. Compliance lives on Prompt Cards (dynamic lookup) and/or the parent-only gate.

**OKF discovery budget:** After the mandated `lookup --card`, at most **one** extra `okf.py lookup` or `okf.py card` for a missing card gap. Then **must write**. Do not Grep/Read `{{GATE_ANSWER_KEY_GLOBS}}` to prepare for the gate.

## Task Under Test

Create a reusable GitHub Actions workflow (`on: workflow_call`) implementing the following stages:

1. build-preprocess
2. build-test-lint
3. owasp
4. sonarqube
5. sonarqube-gate
6. publish-to-nexus
7. docker-build-publish
8. notification-email

### Functional Requirements

- Build once, reuse everywhere.
- Proper `needs:` graph.
- Efficient dependency caching.
- Artifact sharing between stages.
- OWASP Dependency Check report must be imported into SonarQube.
- SonarQube Quality Gate must block publish.
- Publish to Nexus only after Quality Gate passes.
- Docker stage consumes existing build artifacts.
- Notification runs with `if: always()`.
- Include README documenting:
  - inputs
  - outputs
  - secrets
  - artifact flow
  - cache strategy
  - dependency graph
  - usage exampl

### Functional Requirements (shared — no policy language)

Document functional needs inside `{{TASK_DESCRIPTION}}` (stages, artifact flow, README sections, etc.). Do **not** encode org compliance there.

### Parent-only success gate

Parent verifies with `{{PARENT_GATE}}` (customize per task), plus a functional checklist, for example:

- Required deliverables exist
- Documented functional requirements are met
- README / docs completeness (if required by the task)
- **Org / policy gate** (parent only): e.g. Conftest / lint / tests — **do not paste this command or its rules into the baseline initial prompt**

### Output paths (must differ)

- OKF arm writes to: {{OUT_DIR_OKF}}
- no-OKF arm writes to: {{OUT_DIR_NO_OKF}}

### Model

Use the same model for both Tasks: {{MODEL — or "same as parent"}}

### Deliverables (per arm)

{{DELIVERABLES — e.g. workflow.yml + README.md}}

---

## Launch TWO subagents IN ONE TURN (parallel)

### Subagent A (OKF)

- description: okf-min-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST follow the aegis-system protocol for this run.

Package root: {{AEGIS_PATH}}
Control plane: {{AEGIS_PATH}}/AGENTS.md
Brain: {{AEGIS_PATH}}/_okf_knowledge/

Must use:
- Aegis
- AGENTS.md (lookup-first; Prompt Pack is DYNAMIC from live lookup — not a static path ban-list)
- OKF lookup / card Prompt Cards only for org/compliance
- Inject Prompt Cards only

FORBIDDEN (this bench task):
- Dumping vault contents (no graph.json, context dumps, or full vault/standard bodies)
- Reading or grepping this task’s gate answer keys: {{GATE_ANSWER_KEY_GLOBS}}
- Mining the monorepo or network for pins/versions/rule IDs that should be on cards
- Opening grader sources “to pass the gate” before or while authoring

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

BEFORE writing any files:
1. Run:
   python3 {{AEGIS_PATH}}/_okf_knowledge/kernel/okf.py lookup --card --limit 3 "{{LOOKUP_QUERY}}"
2. Inject ONLY the returned ## Prompt Card text into your working context (live pack for this domain).
3. Do NOT paste graph.json, context dumps, or full vault/standard bodies.
4. Treat those Prompt Cards as the ONLY source of org/compliance constraints for this task.
5. Discovery budget: at most ONE extra `okf.py lookup` or `okf.py card` if a required pin/version/rule is missing from the first cards. Then you MUST write — do not Grep {{GATE_ANSWER_KEY_GLOBS}}.

Then complete this task (functional brief only — compliance comes from cards):
{{TASK_DESCRIPTION}}

Deliverables:
{{DELIVERABLES}}

Write outputs ONLY under: {{OUT_DIR_OKF}}
Stop when the deliverables meet the functional brief and your injected Prompt Cards, or after at most {{MAX_FIX_TURNS}} remediation turn(s).

Do NOT expect a parent policy command in this prompt. Apply card constraints yourself.
If you self-run a lint/gate tool, you may only validate files you wrote under {{OUT_DIR_OKF}} — never open {{GATE_ANSWER_KEY_GLOBS}} to prepare.

Return JSON ONLY (no markdown fence):
{
  "arm": "okf_min",
  "wall_s": <float seconds for your whole run>,
  "status": "PASS" | "FAIL",
  "gate_detail": "<short — functional + card compliance self-check>",
  "files_written": ["..."],
  "prompt_chars": <int approx chars of prompts/cards you used>,
  "output_chars": <int approx chars of assistant text + file contents written>,
  "round_trips": <int count of your tool-call turns, including remediation>,
  "notes": "<short — must mention if any extra okf lookup was used>"
}
```

### Subagent B (Baseline)

- description: no-okf-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST NOT use aegis-system / OKF for this run.

Must NOT use:
- AGENTS.md
- OKF
- Prompt Cards
- Vault
- Standards from Aegis

FORBIDDEN (this bench task):
- Reading {{AEGIS_PATH}}/AGENTS.md
- Reading anything under {{AEGIS_PATH}}/_okf_knowledge/
- Running okf.py lookup / okf.py card
- Using Prompt Cards, vault playbooks, or standards from Aegis
- Reading this task’s gate answer keys: {{GATE_ANSWER_KEY_GLOBS}}
- Using org pin lists, rule IDs, or gate commands from memory of this monorepo’s docs (general public knowledge for the domain only)

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

Complete this task from general public knowledge only (no Aegis, no repo policy trees):
{{TASK_DESCRIPTION}}

Deliverables:
{{DELIVERABLES}}

Write outputs ONLY under: {{OUT_DIR_NO_OKF}}
Stop when the deliverables meet the functional brief, or after at most {{MAX_FIX_TURNS}} remediation turn(s).

There is NO policy/compliance gate in this prompt. Do not hunt for Conftest, SPVS, or Rego.

Return JSON ONLY (no markdown fence):
{
  "arm": "no_okf",
  "wall_s": <float seconds for your whole run>,
  "status": "PASS" | "FAIL",
  "gate_detail": "<short — functional self-check only>",
  "files_written": ["..."],
  "prompt_chars": <int>,
  "output_chars": <int>,
  "round_trips": <int count of your tool-call turns, including remediation>,
  "notes": "<short>"
}
```

---

## Parent Verification

Re-run `{{PARENT_GATE}}` on both outputs.

Do **not** trust subagent PASS/FAIL.

### Isolation audit (required — uses this task’s globs)

Parent **MUST** audit transcripts against **`{{GATE_ANSWER_KEY_GLOBS}}`** (not a global path list):

Flag OKF isolation FAIL (even if `{{PARENT_GATE}}` PASSes) if the arm:

- Read/Grep’d any path matching `{{GATE_ANSWER_KEY_GLOBS}}`
- Mined monorepo/network for org pins/rule IDs that should have come from Prompt Cards
- Exceeded the discovery budget (more than one extra `okf.py lookup|card` before first write for grader archaeology)

Baseline isolation FAIL if it touched Aegis/OKF or `{{GATE_ANSWER_KEY_GLOBS}}`.

Record `isolation_okf` / `isolation_base` as PASS|FAIL in parent findings. Gate PASS + isolation FAIL is **not** a clean OKF win.

### Gate FAIL → fix loop (required — true cost-to-PASS)

This is mandatory. A first-draft FAIL is not a final result.

1. Run `{{PARENT_GATE}}` (and any parent checklist) yourself on each arm’s outputs.
2. If **PASS**: keep that arm’s initial metrics as true totals.
3. If **FAIL**:
   - Do **not** implement the fix in the parent.
   - Resume **only the failing arm** (same model, same isolation rules).
   - Paste the **full raw gate/failure output** into the resume prompt (this may reveal policy details — that cost counts toward true cost-to-PASS).
   - Baseline remains forbidden from `{{GATE_ANSWER_KEY_GLOBS}}` / Aegis; it may only use the pasted failure text + its own files.
   - Instruct the arm to fix the issues and stop when PASS or after at most {{MAX_GATE_FIX_LOOPS — e.g. 2}} parent feedback loops.
   - Parent re-runs `{{PARENT_GATE}}` after each loop.
4. **True metrics** for a remediated arm = initial run + all remediation loops (`wall_s`, `round_trips`, `prompt_chars`, `output_chars`, tokens, USD).
5. Report both “draft wall” and “true wall” (and loop count) when remediation occurred.
6. Effectiveness / Efficiency use the **final parent-verified** gate status and **true** wall time.

### Resume prompt template (failing arm only)

Use this as the Task `resume` prompt body (keep arm isolation unchanged):

    Parent verification FAILED the gate. You must fix the issues, then re-check.

    Keep the same arm rules as your original run:
    - OKF: live Prompt Cards only; still FORBIDDEN from {{GATE_ANSWER_KEY_GLOBS}} and pin/rule mining outside cards.
    - Baseline: still forbidden from Aegis/OKF and from {{GATE_ANSWER_KEY_GLOBS}}.

    Record remediation start: date +%s.%N

    Write ONLY under your original output directory.
    Do not touch the other arm's files.

    Failure output (fix until parent gate passes — use only this text + your files; do not open policy trees):
    ---
    {{GATE_FAILURE_OUTPUT}}
    ---

    After fixing, stop. Max {{MAX_FIX_TURNS}} self-remediation turns this loop.
    Parent will re-run the gate.

    Return JSON ONLY (no markdown fence):
    {
      "arm": "<okf_min|no_okf>",
      "phase": "gate_remediation",
      "remediation_wall_s": <float>,
      "total_wall_s_including_original": <float>,
      "original_wall_s": <float>,
      "status": "PASS" | "FAIL",
      "gate_detail": "<short>",
      "files_written": ["..."],
      "prompt_chars": <int this remediation>,
      "output_chars": <int this remediation>,
      "round_trips": <int this remediation>,
      "round_trips_total": <int original + remediation>,
      "notes": "<short>"
    }

---

## Runtime Correctness Audit

Check for (adapt to domain; keep as PASS/FAIL per arm):

- invented actions / APIs / modules
- placeholder actions or masking stubs
- invalid marketplace / registry references
- deprecated actions or APIs
- invalid versions / unpinned mutable refs (when policy requires pins)
- broken SonarQube properties (when applicable)
- broken OWASP import (when applicable)
- cache mistakes
- duplicated builds / duplicated work
- duplicated downloads / redundant I/O
- missing permissions
- excessive permissions
- missing concurrency
- missing timeout
- invalid dependency / `needs` graph
- **card-only isolation** (OKF did not mine `{{GATE_ANSWER_KEY_GLOBS}}`; baseline did not touch Aegis/OKF or those globs)

Score runtime correctness as % of checks PASSED. Isolation FAIL may be tracked separately in Parent Findings even when other checks PASS.

---

## Architecture Review (0–5 each)

- Build Once / Reuse Many
- Artifact Strategy
- Cache Strategy
- Dependency Graph
- Parallelization
- Critical Path Optimization
- Runtime Efficiency
- Failure Isolation
- Security Hardening
- Maintainability
- Reusability
- Enterprise Readiness

**Total: 60**

---

## Performance Metrics

Collect (true totals after any remediation loops):

**Scored (use for winner / ROI):**

- **True Wall Time** = draft wall + all remediation walls (never score draft-only when gate FAIL)
- **Parent runs to PASS** (1 vs 2+ when gate fix loops run)
- Prompt Characters / Output Characters (true totals across runs)
- Input Tokens (`prompt_chars / 4`) / Output Tokens / Total Tokens
- Estimated Cost (`${{IN_PRICE_PER_M}}/M` in, `${{OUT_PRICE_PER_M}}/M` out unless overridden)
- Files Written / Deliverable Size
- Effectiveness (`1` if parent-verified final PASS else `0`)
- Efficiency (`PASS → 1 / true_wall_s`, else `0`)

**Informational only (winner must be `—`; do not crown Baseline on these):**

- Draft Wall (label gate FAIL / not final when applicable)
- Tool-call turns (show draft+rem breakdown; fewer turns ≠ fewer parent runs)
- Throughput (tokens/sec, chars/sec) — higher ≠ better (rem dumps inflate)

---

## Derived Metrics

Calculate:

- Time Saved
- Token Savings
- Cost Savings
- Turn Reduction
- Cache Reuse (qualitative / observed)
- Duplicate Work Eliminated (qualitative / observed)
- Quality Index (0–100)
- Engineering ROI

### Quality Index

- 40% Parent Verification
- 25% Runtime Correctness
- 20% Architecture Review (`arch_total / 60 * 100`)
- 15% Documentation

### Engineering ROI (OKF vs Baseline)

- Time Saved % (true wall)
- Token Reduction %
- Cost Reduction %
- Parent-run Reduction % (scored); tool-turn counts are informational only
- Architecture Improvement %
- Quality Improvement %
- Runtime Correctness Improvement %
- Estimated Developer Effort Saved

---

## HTML Report

Standalone. Inline CSS. Dark theme. Responsive. No JavaScript.

**Must** render from the template (no custom shells):

```bash
python3 {{AEGIS_PATH}}/render_bench_report.py --list-keys
python3 {{AEGIS_PATH}}/render_bench_report.py \
  --data {{REPORT_DATA_JSON}} \
  --out {{REPORT_HTML}}
```

Build JSON covering every template placeholder. Prefer structured helpers:
`kpis`, `metrics`, `dashboard`, `architecture`, `runtime`, `parent_findings`,
`benefits_okf`, `benefits_base`, `methodology`, `verdict_lines`.

### Sections (fixed by template — do not reorder/remove)

1. Executive Summary
2. Winner Banner
3. KPI Cards
4. Performance Dashboard
5. Full Metrics Table
6. Architecture Review
7. Runtime Correctness Audit
8. Artifact & Cache Flow
9. Benefits Observed
10. Parent Findings
11. Methodology
12. Final Verdict

### KPI Cards (each shows OKF / Baseline / Delta / Winner)

**Scored** (`kind: scored` in report JSON):

- True Wall (scored) — show baseline as `draft+rem=true` when rem ran
- Parent Runs (scored)
- Input Tokens / Output Tokens / Total Tokens
- Estimated Cost
- Effectiveness / Efficiency (`1/true_wall`)
- Quality Index / Architecture Score / Runtime Correctness

**Informational** (`kind: info`; winner `—`):

- Tool Turns (info) — e.g. `15` vs `5+5=10`
- Optional: Throughput (info)

When a feedback loop ran, dashboard bars **must** stack baseline draft + remediation into true totals. Never present draft-only wall as the Wall KPI winner.

Append both results to `{{RESULTS_JSONL}}`.

---

## Final Verdict

Summarize in **maximum 6 lines**:

- Fastest
- Lowest Tokens
- Lowest Cost
- Highest Quality
- Best Architecture
- Best Runtime Correctness
- Best Enterprise Readiness
- Overall Winner

---

## Hard Rules

- Same model.
- Parallel execution.
- Parent never performs implementation (including gate fixes — subagents fix; parent only re-verifies).
- No context sharing between arms.
- Parent independently verifies via `{{PARENT_GATE}}` **and** isolation audit against `{{GATE_ANSWER_KEY_GLOBS}}`.
- **Shared task + both initial arm prompts: zero org-compliance text** and no answer-key paths.
- **OKF compliance source: live Prompt Cards** (dynamic lookup per AGENTS.md). **Forbidden** for this task: `{{GATE_ANSWER_KEY_GLOBS}}` and mining pins outside cards.
- **OKF discovery budget:** mandated lookup + at most one extra card/lookup, then write.
- **Baseline: no Aegis; no `{{GATE_ANSWER_KEY_GLOBS}}`.**
- **Gate FAIL → resume failing arm with failure output and fix until PASS (or budget exhausted); score true totals.**
- **Isolation FAIL is reported even when the gate PASSes** (not a clean OKF win).
- HTML report must be self-contained and rendered from `BENCH_REPORT_TEMPLATE.html` via `render_bench_report.py`.
- Do **not** bake domain grader paths into AGENTS.md — keep them in this bench prompt’s placeholders.
```

---

## Placeholder cheat sheet

| Placeholder | Example |
| --- | --- |
| `TASK_DESCRIPTION` | Functional brief only (stages, artifacts, README) — **no** SPVS/Conftest/SHA rules |
| `PARENT_GATE` | Parent-only, e.g. `conftest test …` exits 0 — **not** pasted into baseline initial prompt |
| `DELIVERABLES` | `workflow.yml` and `README.md` |
| `OUT_DIR_OKF` | `{{TARGET_REPO}}/_ab_bench/okf/{{SHORT_NAME}}/` |
| `OUT_DIR_NO_OKF` | `{{TARGET_REPO}}/_ab_bench/no_okf/{{SHORT_NAME}}/` |
| `SHORT_NAME` | `foo-bar` |
| `LOOKUP_QUERY` | task/domain keywords for **live** card lookup (compliance + pin/version cards as needed) |
| `GATE_ANSWER_KEY_GLOBS` | per-gate grader paths only, e.g. GHA Conftest: `**/policies/**` `**/*.rego` (other domains: that gate’s sources) |
| `AEGIS_PATH` | `.cursor/agents/aegis-system` |
| `MAX_FIX_TURNS` | `1` (self-fixes inside one arm turn) |
| `MAX_GATE_FIX_LOOPS` | `2` (parent→arm feedback loops after gate FAIL) |
| `GATE_FAILURE_OUTPUT` | raw stdout/stderr from failed `{{PARENT_GATE}}` (parent pastes on resume only) |
| `MODEL` | `same as parent` |
| `IN_PRICE_PER_M` / `OUT_PRICE_PER_M` | `3` / `15` |
| `RESULTS_JSONL` | `_ab_bench/results.jsonl` |
| `REPORT_HTML` | `_ab_bench/{{SHORT_NAME}}-okf-vs-no-okf-report.html` |
| `REPORT_DATA_JSON` | `_ab_bench/{{SHORT_NAME}}-report-data.json` |

### Example `TASK_DESCRIPTION` (functional only)

```text
Create a reusable GitHub Actions workflow (`on: workflow_call`) with stages:
build-preprocess, build-test-lint, owasp, sonarqube, sonarqube-gate,
publish-to-nexus, docker-build-publish, notification-email.

Requirements: build once; proper needs:; caching; artifact sharing;
OWASP report imported into SonarQube; quality gate blocks publish;
Nexus only after gate; Docker consumes build artifacts; notification if: always();
README covers inputs/outputs/secrets/artifact flow/cache/dependency graph/usage.
```

### Example `PARENT_GATE` (parent only — never in baseline initial prompt)

```text
cd {{TARGET_REPO}} && conftest test --parser yaml -n workflow \
  -p policies/conftest/github_actions/workflow \
  -p policies/conftest/github_actions/lib \
  {{OUT_DIR}}/workflow.yml
```

---

## HTML report template

| File | Role |
| --- | --- |
| [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html) | Dark, responsive, no-JS shell with `{{PLACEHOLDER}}` markers + baked-in scoring contract (true wall / parent runs scored; draft wall, tool turns, tok/s informational) |
| [`render_bench_report.py`](render_bench_report.py) | Fills placeholders; KPI `kind: scored|info`; metric `info: true` for non-scoring rows |

```bash
python3 .cursor/agents/aegis-system/render_bench_report.py --list-keys

python3 .cursor/agents/aegis-system/render_bench_report.py \
  --data _ab_bench/my-task-report-data.json \
  --out _ab_bench/my-task-okf-vs-no-okf-report.html
```

Set `METHODOLOGY_NOTE_CLASS` to `hidden` when there is no remediation note; otherwise leave it empty and put the note in `METHODOLOGY_NOTE`.

---

## Related

- Protocol: [`AGENTS.md`](AGENTS.md) (§1.5 lookup)
- Architecture: [`ADR.md`](ADR.md)
- Injection rule: [`_okf_knowledge/standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md)
- Report template: [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html)
- Report renderer: [`render_bench_report.py`](render_bench_report.py)
