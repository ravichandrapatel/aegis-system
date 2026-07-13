# A/B Bench Prompt — OKF vs no-OKF

Copy this entire file into a Cursor chat (or `@`-mention it), fill every `{{...}}` placeholder, then send.

The parent agent **orchestrates only**: two parallel Task subagents (same model), metrics, then a canvas plot. It must **not** implement the task itself.

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

BEFORE writing any files:
1. Run:
   python3 {{AEGIS_PATH}}/_okf_knowledge/kernel/okf_lookup.py --card --limit 3 "{{LOOKUP_QUERY}}"
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
- Running okf_lookup.py / prompt_card.py
- Using Prompt Cards, vault playbooks, or standards from Aegis

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
  "notes": "<short>"
}
```

---

## Parent responsibilities (after both finish)

1. Prefer each subagent’s `wall_s`; if missing, use your observed Task durations.
2. Estimate tokens: `in_tok = prompt_chars/4`, `out_tok = output_chars/4`, `total_tok = in_tok + out_tok`.
3. Estimate USD (unless I override): ${{IN_PRICE_PER_M — e.g. 3}}/M input, ${{OUT_PRICE_PER_M — e.g. 15}}/M output.
4. Effectiveness: `1` if status==PASS else `0` (also keep gate_detail).
5. Efficiency: if PASS → `1/wall_s`, else `0`.
6. Append both results to `{{RESULTS_JSONL — e.g. _ab_bench/results.jsonl}}`.
7. Create/update a Cursor canvas `{{CANVAS_NAME — e.g. okf-vs-no-okf-ab.canvas.tsx}}` with:
   - Stats: wall_s, total_tok, USD, PASS/FAIL per arm
   - BarChart: wall_s by arm
   - BarChart: total_tok by arm
   - Table: effectiveness, efficiency, notes
8. Reply with a ≤6 line verdict: winner on time-to-PASS, tokens, cost, effectiveness.

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
| `CANVAS_NAME` | `okf-vs-no-okf-ab.canvas.tsx` |

## Related

- Protocol: [`AGENTS.md`](AGENTS.md) (§1.5 lookup)
- Architecture: [`ADR.md`](ADR.md)
- Injection rule: [`_okf_knowledge/standards/okf-prompt-injection.md`](_okf_knowledge/standards/okf-prompt-injection.md)
