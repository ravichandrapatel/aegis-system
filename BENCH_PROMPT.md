# A/B Bench Prompt — OKF vs no-OKF

Copy this entire file into a Cursor chat (or `@`-mention it), fill every `{{...}}` placeholder, then send.

The parent agent **orchestrates only**: two parallel Task subagents (same model), metrics, then a standalone **HTML report**. It must **not** implement the task itself.

**Aegis is not automatic for subagents.** The OKF arm must be told to use Aegis; the no-OKF arm must be told not to.

---

```text
# A/B bench: OKF vs no-OKF (parent orchestrator only)

You are the parent. Do **not** implement the task yourself.
Launch **two Task subagents in parallel** (same model), collect metrics, then plot.

## Task under test (I decide this)
{{TASK_DESCRIPTION}}

### Success gate
{{GATE — e.g. policy scan pass, tests green, file X exists, lint clean}}

### Output paths (must differ)
- OKF arm writes to: {{OUT_DIR_OKF}}
- no-OKF arm writes to: {{OUT_DIR_NO_OKF}}

### Model
Use the same model for both Tasks: {{MODEL — or "same as parent"}}

---

## Launch TWO subagents IN ONE TURN (parallel)

### Subagent A — okf_min
- description: okf-min-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST follow the aegis-system protocol for this run.

Package root: {{AEGIS_PATH — e.g. .cursor/agents/aegis-system}}
Control plane: {{AEGIS_PATH}}/AGENTS.md
Brain: {{AEGIS_PATH}}/_okf_knowledge/

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

BEFORE writing any files:
1. Run:
   python3 {{AEGIS_PATH}}/_okf_knowledge/kernel/okf.py lookup --card --limit 3 "{{LOOKUP_QUERY}}"
2. Inject ONLY the returned ## Prompt Card text into your working context.
3. Do NOT paste graph.json, context dumps, or full vault/standard bodies.

Then complete this task:
{{TASK_DESCRIPTION}}

Write outputs ONLY under: {{OUT_DIR_OKF}}
Stop when the gate passes, or after at most {{MAX_FIX_TURNS — e.g. 1}} remediation turn(s).

Gate:
{{GATE}}

Return JSON ONLY (no markdown fence):
{
  "arm": "okf_min",
  "wall_s": <float seconds for your whole run>,
  "status": "PASS" | "FAIL",
  "gate_detail": "<short>",
  "files_written": ["..."],
  "prompt_chars": <int approx chars of prompts/cards you used>,
  "output_chars": <int approx chars of assistant text + file contents written>,
  "round_trips": <int count of your tool-call turns, including remediation>,
  "notes": "<short>"
}
```

### Subagent B — no_okf
- description: no-okf-{{SHORT_NAME}}
- subagent_type: generalPurpose
- prompt:

```
You MUST NOT use aegis-system / OKF for this run.

FORBIDDEN:
- Reading {{AEGIS_PATH}}/AGENTS.md
- Reading anything under {{AEGIS_PATH}}/_okf_knowledge/
- Running okf.py lookup / okf.py card
- Using Prompt Cards, vault playbooks, or standards from Aegis

Record your start time (`date +%s.%N`) FIRST so you can report wall_s at the end.

Complete this task from general knowledge / the target repo only:
{{TASK_DESCRIPTION}}

Write outputs ONLY under: {{OUT_DIR_NO_OKF}}
Stop when the gate passes, or after at most {{MAX_FIX_TURNS}} remediation turn(s).

Gate:
{{GATE}}

Return JSON ONLY (no markdown fence):
{
  "arm": "no_okf",
  "wall_s": <float seconds for your whole run>,
  "status": "PASS" | "FAIL",
  "gate_detail": "<short>",
  "files_written": ["..."],
  "prompt_chars": <int>,
  "output_chars": <int>,
  "round_trips": <int count of your tool-call turns, including remediation>,
  "notes": "<short>"
}
```

---

## Parent responsibilities (after both finish)

1. **Re-run the gate yourself on both outputs** — do not trust self-reported status. Record parent-verified gate results.
2. Prefer each subagent’s `wall_s`; if missing, use your observed Task durations.
3. Estimate tokens: `in_tok = prompt_chars/4`, `out_tok = output_chars/4`, `total_tok = in_tok + out_tok`.
4. Estimate USD (unless I override): ${{IN_PRICE_PER_M — e.g. 3}}/M input, ${{OUT_PRICE_PER_M — e.g. 15}}/M output.
5. Effectiveness: `1` if status==PASS else `0` (also keep gate_detail).
6. Efficiency: if PASS → `1/wall_s`, else `0`.
7. Audit quality beyond the gate: skim both artifacts for domain misses (invented refs, wrong runners, placeholder values) and optionally run an advisory linter not in the gate.
8. Append both results to `{{RESULTS_JSONL — e.g. _ab_bench/results.jsonl}}`.
9. Write a standalone, self-contained **HTML report** to `{{REPORT_HTML — e.g. _ab_bench/okf-vs-no-okf-report.html}}` (inline CSS, no external deps, dark theme, no JS needed). Sections in order:
   - Header: task one-liner, model, gate, date
   - Verdict banner: winner + the headline deltas in one paragraph
   - Stat cards: time-to-PASS, total tokens, USD, round trips (each with % delta)
   - Bar charts (pure CSS width bars): wall_s per arm; tokens per arm (total + in/out split); USD per arm
   - Full metric table: gate status (parent-verified), wall_s, round_trips, prompt/output chars, in/out/total tokens, USD, effectiveness, efficiency, deliverable sizes — winner column per row
   - Quality review table: parent audit findings per arm (domain correctness, hygiene, advisory lint)
   - Benefits observed: bullets per arm + what the gate equalized
   - Round-trip breakdown: turns per arm and what they went to
   - Methodology footnote: isolation, gate command, token estimation method, pricing assumption, single-run caveat
10. Reply with a ≤6 line verdict: winner on time-to-PASS, tokens, cost, effectiveness, plus any runtime-correctness gap the gate missed.

## Hard rules
- Same model both arms.
- Do not share one arm’s outputs/context with the other.
- Do not implement the task in the parent.
- OKF arm = explicit Aegis + lookup cards; no-OKF arm = explicit forbid Aegis.
```

---

## Placeholder cheat sheet

| Placeholder | Example |
| --- | --- |
| `TASK_DESCRIPTION` | Add module `foo-bar` with the required artifacts |
| `GATE` | Domain lint / policy scan exits 0 |
| `OUT_DIR_OKF` | `{{TARGET_REPO}}/_ab_bench/okf/foo-bar/` |
| `OUT_DIR_NO_OKF` | `{{TARGET_REPO}}/_ab_bench/no_okf/foo-bar/` |
| `SHORT_NAME` | `foo-bar` |
| `LOOKUP_QUERY` | `prompt injection simplicity` |
| `AEGIS_PATH` | `./aegis-system` (or `.cursor/agents/aegis-system`) |
| `MAX_FIX_TURNS` | `1` |
| `MODEL` | `same as parent` |
| `IN_PRICE_PER_M` / `OUT_PRICE_PER_M` | `{{IN_PRICE_PER_M}}` / `{{OUT_PRICE_PER_M}}` |
| `RESULTS_JSONL` | `_ab_bench/results.jsonl` |
| `REPORT_HTML` | `_ab_bench/okf-vs-no-okf-report.html` |

---

## Worked example — npm CI/CD reusable workflow (run 2026-07-14, composer-2.5-fast)

Filled placeholders from a real run against `gha-reusable-actions-workflows`:

| Placeholder | Value used |
| --- | --- |
| `TASK_DESCRIPTION` | See detailed task below |
| `SHORT_NAME` | `npm-ci-cd` |
| `LOOKUP_QUERY` | `reusable workflow spvs` |
| `AEGIS_PATH` | `/home/ghost/workspace-latest/.cursor/agents/aegis-system` |
| `OUT_DIR_OKF` | `gha-reusable-actions-workflows/_ab_bench/okf/npm-ci-cd/` |
| `OUT_DIR_NO_OKF` | `gha-reusable-actions-workflows/_ab_bench/no_okf/npm-ci-cd/` |
| `MODEL` | `composer-2.5-fast` |
| `MAX_FIX_TURNS` | `1` |
| `IN_PRICE_PER_M` / `OUT_PRICE_PER_M` | `3` / `15` |
| `RESULTS_JSONL` | `gha-reusable-actions-workflows/_ab_bench/results.jsonl` |
| `REPORT_HTML` | `gha-reusable-actions-workflows/_ab_bench/okf-vs-no-okf-report.html` |

### TASK_DESCRIPTION (detailed)

```text
Create a reusable GitHub Actions workflow (`on: workflow_call`) for an npm
application, as a component of the monorepo at
gha-reusable-actions-workflows. It must be multi-stage with proper job
dependencies (needs:):
1. build (npm ci + npm run build, upload artifact)
2. test (npm test)
3. lint (npm run lint)
4. owasp (OWASP dependency check scan)
5. sonarqube (SonarQube scan)
6. publish (npm publish, only after all quality gates)
7. docker (docker build & push)
8. notify (email notification of the run result, always runs)

Deliverables: `workflow.yml` and a short `readme.md`
(inputs/secrets/outputs + one usage example).
```

### GATE (run from the monorepo root)

```bash
conftest test --parser yaml -n workflow \
  -p policies/conftest/github_actions/workflow \
  -p policies/conftest/github_actions/lib \
  _ab_bench/{okf|no_okf}/npm-ci-cd/workflow.yml
# PASS when exit code is 0
```

### Result snapshot

| Metric | okf_min | no_okf |
| --- | ---: | ---: |
| Gate (parent-verified) | PASS 26/26, one-shot | PASS 26/26, one-shot |
| wall_s | 67.96 | 85.43 |
| Round trips | 8 | 9 |
| Total tokens (est.) | 3,965 | 5,325 |
| USD (est.) | $0.0572 | $0.0736 |

Key quality finding the gate missed: the no-OKF arm invented a placeholder
`my-org/...@v1` OWASP action reference on `ubuntu-latest` (runtime-broken);
the OKF arm used the repo's local `./actions/security/owasp-dependency-check`
on `[self-hosted, podman]` per vault knowledge. Full report:
`_ab_bench/okf-vs-no-okf-report.html`.

## Related

- Protocol: [`AGENTS.md`](AGENTS.md) (§1.5 lookup)
- Architecture: [`ADR.md`](ADR.md)
- Injection rule: [`_okf_knowledge/standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md)
