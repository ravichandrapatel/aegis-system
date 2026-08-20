# A/B Benchmark — OKF vs no-OKF

> **Purpose**
>
> Benchmark whether the OKF knowledge system improves engineering outcomes over a baseline model by running two isolated subagents on the same task using the same model.

Copy this file into a Cursor chat (or `@`-mention it), fill every `{{...}}` placeholder, then send.

The parent agent **orchestrates only**. It must **not** implement the task itself.
If a parent-run gate fails, the parent **must** feed the failure back to that arm for fixes and re-score true cost-to-PASS (never treat a draft FAIL as final without the fix loop).

**HTML report must use the checked-in template** — do not hand-author a new layout:

- Template: [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html) (repo root)
- Renderer: [`render_bench_report.py`](render_bench_report.py) (repo root)

**OKF is not automatic for subagents.** The OKF arm must be told to use OKF; the no-OKF arm must be told not to.

**Compliance knowledge isolation (hard):** Org compliance and the **answer-key sources for this task’s `{{PARENT_GATE}}`** MUST NOT appear in the shared task brief or either arm’s initial prompt. The OKF arm obtains compliance **only** via a live Prompt Pack from `okf.py pack` (dynamic per domain — see [`AGENTS.md`](AGENTS.md) Rule #1 and [`.cursor/rules/okf.mdc`](.cursor/rules/okf.mdc)). Fill `{{GATE_ANSWER_KEY_GLOBS}}` with the grader paths for **this** gate only (Flask CI example: `**/policies/**`, `**/*.rego`, or the repo’s workflow Conftest dirs). Do not put a universal path ban into AGENTS.md. Parent runs `{{PARENT_GATE}}` and an isolation audit against those globs.

---

```text
# A/B Benchmark — OKF vs no-OKF (parent orchestrator only)

You are the parent. Do **not** implement the task.

## Parent Responsibilities

- Do **not** implement the task.
- Launch **two parallel subagents** (same model).
- Verify outputs independently (re-run {{PARENT_GATE}} yourself).
- **Never put {{PARENT_GATE}}, Conftest, Rego paths, pin/SHA rules, or grader trees into the baseline arm’s initial prompt.**
- **If the parent gate fails for either arm: feed the failure output back to that arm and make it fix the issues** (do not score a draft FAIL as final).
- Re-verify after each fix loop until PASS or remediation budget is exhausted.
- Score **true cost-to-PASS** (initial + all remediation loops).
- Produce a standalone HTML benchmark report from BENCH_REPORT_TEMPLATE.html via render_bench_report.py.

## Knowledge isolation (mandatory)

| Source | OKF arm | Baseline arm | Parent |
| --- | --- | --- | --- |
| Shared `{{TASK_DESCRIPTION}}` | Functional only | Functional only | — |
| OKF Prompt Pack / Prompt Cards (live `okf.py pack`) | **Required** (only compliance source) | Forbidden | — |
| `{{GATE_ANSWER_KEY_GLOBS}}` (grader for this gate) | **Forbidden** | **Forbidden** | May read to run gate |
| Pins/versions/catalogs | From **cards** only | Public knowledge only | — |
| `{{PARENT_GATE}}` | Not in initial prompt | **Not in initial prompt** | Runs for score |
| Gate failure stdout on resume | Allowed (fix loop) | Allowed (fix loop) | Pastes raw output |

`{{GATE_ANSWER_KEY_GLOBS}}` is **per task / per gate** — not a global AGENTS.md list. Example for a sample Flask GHA Conftest gate: `**/policies/**`, `**/*.rego`, Conftest policy dirs used by `{{PARENT_GATE}}`. For another domain, name that domain’s grader paths instead.

Shared task text and both initial arm prompts MUST be free of org-compliance text and those answer-key paths. Compliance lives on Prompt Cards (dynamic pack) and/or the parent-only gate.

**OKF discovery budget (aligns with AGENTS.md / .cursor / .github):** Run **one** `okf.py pack` before authoring. Inject **only** returned Prompt Card text. An **empty pack is valid** — proceed on judgement; do **not** re-pack for a hit. Need more? Follow a card’s `related:` / `source:` edge (or browse `_okf_knowledge/index.md`) — do **not** re-query pack. Do not Grep/Read `{{GATE_ANSWER_KEY_GLOBS}}` to prepare for the gate. Do not paste `index.json`, `graph.json`, or full vault/standard bodies.

## Task Under Test

Create a **reusable GitHub Actions workflow for a Python Flask application** (`on: workflow_call`) that CI-builds, tests, scans, and publishes a Flask service. Implement these stages:

1. setup-python-deps
2. lint-format
3. unit-test
4. security-scan (SAST / dependency)
5. coverage-quality-gate
6. build-package (sdist/wheel or app artifact)
7. docker-build-publish
8. notification

### Functional Requirements

- Target app shape: Flask (WSGI) service with `requirements.txt` or `pyproject.toml`, pytest suite, and a Dockerfile — the workflow must assume that layout via inputs (do not invent a full app unless listed in deliverables).
- Build / install dependencies **once**; reuse across jobs via cache + artifacts.
- Proper `needs:` graph; no redundant reinstalls when artifacts exist.
- Efficient pip/venv (or poetry/uv) caching keyed on the lock/requirements hash.
- Artifact sharing between stages (test reports, coverage XML, build artifact, image metadata).
- Security scan results available to the quality gate (fail the pipeline on policy-defined severity).
- Coverage / quality gate **must block** package publish and image publish.
- Publish package artifact only after the quality gate passes.
- Docker stage consumes the **existing** build artifact (do not rebuild the app from scratch in the image job unless inputs say otherwise).
- Notification job runs with `if: always()`.
- Pin third-party Actions to full 40-character commit SHAs (with version comments); workflow `permissions:` least privilege.
- Include README documenting:
  - inputs
  - outputs
  - secrets
  - Python/Flask assumptions (entry module, test path, Docker context)
  - artifact flow
  - cache strategy
  - dependency graph
  - usage example (`workflow_call` consumer)

### Functional Requirements (shared — no policy language)

Document functional needs inside `{{TASK_DESCRIPTION}}` (stages, artifact flow, README sections, Flask layout assumptions, etc.). Do **not** encode org compliance there.

### Parent-only success gate

Parent verifies with `{{PARENT_GATE}}` (customize per task), plus a functional checklist, for example:

- Required deliverables exist
- Documented functional requirements are met
- README / docs completeness (if required by the task)
- **Org / policy gate** (parent only): e.g. Conftest / actionlint / workflow lint — **do not paste this command or its rules into the baseline initial prompt**

### Output paths (must differ)

- OKF arm writes to: {{OUT_DIR_OKF}}
- no-OKF arm writes to: {{OUT_DIR_NO_OKF}}

### Model

Use the same model for both arms: {{MODEL — or "same as parent"}}

### Deliverables (per arm)

{{DELIVERABLES — e.g. .github/workflows/flask-ci.yml + README.md}}

---

## Launch TWO subagents IN ONE TURN (parallel)

### Subagent A (OKF)

- description: okf-min-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST follow the OKF protocol for this run (AGENTS.md + .cursor/rules/okf.mdc).

Package root: {{AEGIS_PATH}}
Control plane: {{AEGIS_PATH}}/AGENTS.md
Brain: {{AEGIS_PATH}}/_okf_knowledge/
Cursor DNA: {{AEGIS_PATH}}/.cursor/rules/okf.mdc
Copilot DNA (same Rule #1): {{AEGIS_PATH}}/.github/copilot-instructions.md

Must use:
- OKF
- AGENTS.md Rule #1 — Pack first (Prompt Pack is DYNAMIC from live pack — not a static path ban-list)
- Live `okf.py pack` Prompt Cards only for org/compliance
- Inject Prompt Card text only

FORBIDDEN (this bench task):
- Dumping vault contents (no graph.json, index.json, context dumps, or full vault/standard bodies)
- Reading or grepping this task’s gate answer keys: {{GATE_ANSWER_KEY_GLOBS}}
- Mining the monorepo or network for pins/versions/rule IDs that should be on cards
- Opening grader sources “to pass the gate” before or while authoring
- Re-packing after an empty or partial pack (follow related:/source: instead)
- Claiming compliance without having run pack

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

BEFORE writing any files:
1. Run ONCE:
   python3 {{AEGIS_PATH}}/_okf_knowledge/kernel/okf.py pack --budget 1200 "{{LOOKUP_QUERY}}"
2. Inject ONLY the returned Prompt Card text into your working context (live pack for this domain).
3. Do NOT paste graph.json, index.json, context dumps, or full vault/standard bodies.
4. Treat those Prompt Cards as the ONLY source of org/compliance constraints for this task.
5. Discovery budget: **one pack only**. If a required pin/version/rule is missing, follow a card’s `related:` / `source:` edge or browse `_okf_knowledge/index.md` — do **not** re-pack and do **not** Grep {{GATE_ANSWER_KEY_GLOBS}}. Empty pack → proceed on judgement and write.

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
  "notes": "<short — must mention pack empty/non-empty and whether related: edges were followed>"
}
```

### Subagent B (Baseline)

- description: no-okf-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST NOT use OKF / the aegis-system brain for this run.

Must NOT use:
- AGENTS.md
- .cursor/rules/okf.mdc
- .github/copilot-instructions.md
- OKF
- Prompt Cards / Prompt Packs
- Vault under _okf_knowledge/
- Standards from OKF

FORBIDDEN (this bench task):
- Reading {{AEGIS_PATH}}/AGENTS.md
- Reading anything under {{AEGIS_PATH}}/_okf_knowledge/
- Reading {{AEGIS_PATH}}/.cursor/rules/okf.mdc or OKF skills/commands
- Running okf.py pack / lookup / card
- Using Prompt Cards, vault playbooks, or standards from OKF
- Reading this task’s gate answer keys: {{GATE_ANSWER_KEY_GLOBS}}
- Using org pin lists, rule IDs, or gate commands from memory of this monorepo’s docs (general public knowledge for Flask/Python CI only)

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

Complete this task from general public knowledge only (no OKF, no repo policy trees):
{{TASK_DESCRIPTION}}

Deliverables:
{{DELIVERABLES}}

Write outputs ONLY under: {{OUT_DIR_NO_OKF}}
Stop when the deliverables meet the functional brief, or after at most {{MAX_FIX_TURNS}} remediation turn(s).

There is NO policy/compliance gate in this prompt. Do not hunt for Conftest, Rego, or org grader trees.

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
- Violated pack-once / no-repack rules (re-packed after empty/partial; or dumped graph/index/full docs)

Baseline isolation FAIL if it touched OKF / `_okf_knowledge/` / OKF Cursor·GitHub DNA or `{{GATE_ANSWER_KEY_GLOBS}}`.

Record `isolation_okf` / `isolation_base` as PASS|FAIL in parent findings. Gate PASS + isolation FAIL is **not** a clean OKF win.

### Gate FAIL → fix loop (required — true cost-to-PASS)

This is mandatory. A first-draft FAIL is not a final result.

1. Run `{{PARENT_GATE}}` (and any parent checklist) yourself on each arm’s outputs.
2. If **PASS**: keep that arm’s initial metrics as true totals.
3. If **FAIL**:
   - Do **not** implement the fix in the parent.
   - Resume **only the failing arm** (same model, same isolation rules).
   - Paste the **full raw gate/failure output** into the resume prompt (this may reveal policy details — that cost counts toward true cost-to-PASS).
   - Baseline remains forbidden from `{{GATE_ANSWER_KEY_GLOBS}}` / OKF; it may only use the pasted failure text + its own files.
   - Instruct the arm to fix the issues and stop when PASS or after at most {{MAX_GATE_FIX_LOOPS — e.g. 2}} parent feedback loops.
   - Parent re-runs `{{PARENT_GATE}}` after each loop.
4. **True metrics** for a remediated arm = initial run + all remediation loops (`wall_s`, `round_trips`, `prompt_chars`, `output_chars`, tokens, USD).
5. Report both “draft wall” and “true wall” (and loop count) when remediation occurred.
6. Effectiveness / Efficiency use the **final parent-verified** gate status and **true** wall time.

### Resume prompt template (failing arm only)

Use this as the Task `resume` prompt body (keep arm isolation unchanged):

    Parent verification FAILED the gate. You must fix the issues, then re-check.

    Keep the same arm rules as your original run:
    - OKF: live Prompt Cards only (pack already done — follow related: edges if needed; still FORBIDDEN from {{GATE_ANSWER_KEY_GLOBS}} and pin/rule mining outside cards).
    - Baseline: still forbidden from OKF and from {{GATE_ANSWER_KEY_GLOBS}}.

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

Check for (adapt to Flask/Python CI; keep as PASS/FAIL per arm):

- invented Actions / APIs / modules
- placeholder Actions or masking stubs
- invalid marketplace / registry references
- deprecated Actions or APIs
- unpinned mutable Action refs (when policy requires 40-char SHA pins)
- Flask/Python layout mismatches (wrong test path, missing PYTHONPATH, wrong module)
- broken coverage / quality-gate wiring
- broken security-scan import into the gate
- cache mistakes (pip cache key ignores lockfile)
- duplicated installs / duplicated builds
- duplicated downloads / redundant I/O
- missing permissions
- excessive permissions
- missing concurrency
- missing timeout
- invalid `needs:` graph
- **card-only isolation** (OKF did not mine `{{GATE_ANSWER_KEY_GLOBS}}`; baseline did not touch OKF or those globs)

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

**Must** render from the checked-in template at **repo root** (no custom shells):

```bash
python3 {{AEGIS_PATH}}/render_bench_report.py --list-keys
python3 {{AEGIS_PATH}}/render_bench_report.py \
  --data {{REPORT_DATA_JSON}} \
  --out {{REPORT_HTML}}
```

Template file: `{{AEGIS_PATH}}/BENCH_REPORT_TEMPLATE.html`

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
- **OKF compliance source: one live `okf.py pack`** (AGENTS.md / `.cursor/rules/okf.mdc` / `.github/copilot-instructions.md` / `.github/instructions/okf-brain.instructions.md`). **Forbidden** for this task: `{{GATE_ANSWER_KEY_GLOBS}}`, re-pack after empty, and mining pins outside cards/`related:` edges.
- **OKF discovery budget:** one pack; then write (follow edges if needed — never dump graph/index).
- **Baseline: no OKF; no `{{GATE_ANSWER_KEY_GLOBS}}`.**
- **Gate FAIL → resume failing arm with failure output and fix until PASS (or budget exhausted); score true totals.**
- **Isolation FAIL is reported even when the gate PASSes** (not a clean OKF win).
- HTML report must be self-contained and rendered from `BENCH_REPORT_TEMPLATE.html` via `render_bench_report.py` at repo root.
- Do **not** bake domain grader paths into AGENTS.md — keep them in this bench prompt’s placeholders.
```

---

## Placeholder cheat sheet

| Placeholder | Example |
| --- | --- |
| `TASK_DESCRIPTION` | Functional Flask CI brief only (stages, artifacts, README) — **no** Conftest/SHA policy text |
| `PARENT_GATE` | Parent-only, e.g. `conftest test …` exits 0 — **not** pasted into baseline initial prompt |
| `DELIVERABLES` | `.github/workflows/flask-ci.yml` and `README.md` |
| `OUT_DIR_OKF` | `{{TARGET_REPO}}/_ab_bench/okf/{{SHORT_NAME}}/` |
| `OUT_DIR_NO_OKF` | `{{TARGET_REPO}}/_ab_bench/no_okf/{{SHORT_NAME}}/` |
| `SHORT_NAME` | `flask-ci` |
| `LOOKUP_QUERY` | e.g. `flask python github actions workflow ci security pin` for **live** pack |
| `GATE_ANSWER_KEY_GLOBS` | per-gate grader paths only, e.g. `**/policies/**` `**/*.rego` |
| `AEGIS_PATH` | repo root of this aegis-system checkout (contains `AGENTS.md`, `_okf_knowledge/`, `render_bench_report.py`) |
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
Create a reusable GitHub Actions workflow (`on: workflow_call`) for a Python Flask app with stages:
setup-python-deps, lint-format, unit-test, security-scan, coverage-quality-gate,
build-package, docker-build-publish, notification.

Assumptions (inputs may override): Flask app module `app:app` or `wsgi:app`;
tests under `tests/` via pytest; deps in `requirements.txt` or `pyproject.toml`;
Dockerfile at repo root.

Requirements: install once and reuse; proper needs:; pip cache; artifact sharing;
security findings feed the quality gate; gate blocks package + image publish;
Docker consumes the build artifact; notification if: always();
pin third-party Actions by full commit SHA; least-privilege permissions:;
README covers inputs/outputs/secrets/Flask layout/artifact flow/cache/dependency graph/usage.
```

### Example `PARENT_GATE` (parent only — never in baseline initial prompt)

```text
cd {{TARGET_REPO}} && conftest test --parser yaml -n workflow \
  -p policies/conftest/github_actions/workflow \
  -p policies/conftest/github_actions/lib \
  {{OUT_DIR}}/.github/workflows/flask-ci.yml
```

---

## HTML report template

| File | Role |
| --- | --- |
| [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html) | Dark, responsive, no-JS shell with `{{PLACEHOLDER}}` markers + baked-in scoring contract (true wall / parent runs scored; draft wall, tool turns, tok/s informational) |
| [`render_bench_report.py`](render_bench_report.py) | Fills placeholders; KPI `kind: scored|info`; metric `info: true` for non-scoring rows |

```bash
python3 render_bench_report.py --list-keys

python3 render_bench_report.py \
  --data _ab_bench/flask-ci-report-data.json \
  --out _ab_bench/flask-ci-okf-vs-no-okf-report.html
```

Set `METHODOLOGY_NOTE_CLASS` to `hidden` when there is no remediation note; otherwise leave it empty and put the note in `METHODOLOGY_NOTE`.

---

## Related

- Protocol: [`AGENTS.md`](AGENTS.md) (Rule #1 — Pack first)
- Cursor rule: [`.cursor/rules/okf.mdc`](.cursor/rules/okf.mdc)
- Copilot instructions: [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
- Copilot brain instructions: [`.github/instructions/okf-brain.instructions.md`](.github/instructions/okf-brain.instructions.md)
- Injection standard: [`_okf_knowledge/standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md)
- Maintain playbook: [`_okf_knowledge/vault/playbooks/maintain-okf-system.md`](_okf_knowledge/vault/playbooks/maintain-okf-system.md)
- Report template: [`BENCH_REPORT_TEMPLATE.html`](BENCH_REPORT_TEMPLATE.html)
- Report renderer: [`render_bench_report.py`](render_bench_report.py)
