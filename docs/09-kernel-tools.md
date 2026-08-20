# 9. Kernel tools

[← Table of contents](README.md)

The kernel entry point is `_okf_knowledge/kernel/okf.py` (thin caller, currently version `1.9.0`). Implementation lives under `_okf_knowledge/kernel/src/` as a **stdlib Python package** with two optional imports: [`kernel/requirements.txt`](../_okf_knowledge/kernel/requirements.txt) (`tiktoken`) for accurate token counts, and **PyYAML** for OKF v0.2 nested frontmatter (`generated`, `verified`, `sources`). Without PyYAML the parser falls back to a flat subset and those documents are reported unparseable (`DBG-002`) rather than mangled — `okf.py capabilities` reports which path is live. Run from the **package directory** (the folder that contains `AGENTS.md`).

```bash
cd /path/to/aegis-system
python3 _okf_knowledge/kernel/okf.py <subcommand> …
```

## Catalog — when to use what

| Subcommand | When to use | Primary outputs | Side effects |
| --- | --- | --- | --- |
| **`okf.py pack`** | **Start here** on non-trivial work — capability line + Prompt Pack in one command | stdout/file pack (md/json/xml) | Read-only |
| **`okf.py capabilities`** | Standalone capability probe (`pack` already prints the short form) | Console or `--json` report | Read-only |
| **`okf.py lookup`** | Ranked menu, paths, or a pack without the caps line | stdout hits / cards | Read-only |
| **`okf.py card`** | Extract cards for known paths | stdout cards | Read-only |
| **`okf.py tokens`** | Measure token cost of files / dirs (no model call) | table or `--json` | Read-only |
| **`okf.py compile`** | After any durable brain edit | `index.json`, `prompt_cards.json`, `kernel/src/graph.json`, HTML graph embed | Writes compiled artifacts |
| **`okf.py lint`** | After edits; CI; pre-merge | console report + HTML lint embed | Rewrites the embed (no `lint.json`) |
| **`okf.py serve`** | Local brain visualizer | HTTP on loopback `:8080` | **Read-only** — serves html/graph only, no mutate endpoints |
| **`okf.py optimize`** | Normalize references / rebuild indexes | Updated reference indexes + compile | Rewrites reference-related indexes; runs compiler |
| **`okf.py scrape`** | JIT fetch upstream docs into vault | New/updated vault markdown | Network + writes under vault |

## `okf.py pack`

**Use when:** any non-trivial task begins. It folds capability discovery into retrieval, so Rule #1 is one command.

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "eks irsa rotation"
python3 _okf_knowledge/kernel/okf.py pack --style json --no-caps "prompt injection"
python3 _okf_knowledge/kernel/okf.py pack --min-score 0 "broad sweep"     # disable the floor
```

| Behavior | Detail |
| --- | --- |
| Capability line | First line of markdown output: `caps: READY \| all present \| features: …`. Suppress with `--no-caps`; not emitted for `--style json/xml`. |
| Exit code | **Always `0`** — an empty pack is a valid answer, not an error |
| Relevance floor | `--min-score` (default `24`) drops weak ranked hits so off-topic queries return nothing |
| Budget | `--max-cards 8` / `--budget 1200`; an oversized single card is truncated, never allowed to blow the budget |
| Traversal | Each card is followed by a `related:` line (graph neighbours) and a `source:` line when the concept sets `resource`. Follow an edge instead of re-packing. No flag — cap is `related_links` in `kernel/src/config.py` (`0` disables) |
| Trust | A `trust:` line appears only when the card is a caution — `unverified`, `machine-confirmed`, or `stale since <date>`. A human-reviewed, fresh card prints nothing |

Full detail: [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md).

## `okf.py capabilities`

**Use when:** `pack` reported something degraded and you want the full table, or you need a machine-readable probe in CI.

```bash
python3 _okf_knowledge/kernel/okf.py capabilities
python3 _okf_knowledge/kernel/okf.py capabilities --json
python3 _okf_knowledge/kernel/okf.py capabilities --strict   # exit 4 when BLOCKED
```

Probes `python`, `filesystem`, `shell`, `brain`, `yaml`, `git`, `compile`, `lint`; reports each as `present` / `degraded` / `missing`, lists enabled features, and summarizes as `READY` or `BLOCKED`. Without `--strict` it always exits `0`.

`yaml` is `present` when PyYAML is importable (which also adds the `okf_v02` enabled feature) and `degraded` when it is missing — the kernel still runs, but OKF v0.2 nested frontmatter will not parse.

## `okf.py lookup`

Full detail: [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md).

**Use when:** you do not already know the concept path; you need ranked candidates or budgeted cards.

## `okf.py card`

**Use when:** paths are already known (e.g. from a previous lookup, or a card that cited a sibling document).

**Do not use when:** you still need discovery — run lookup first.

## `okf.py tokens`

**Use when:** sizing always-on context, Prompt Cards, or any file/directory token cost locally (no API).

```bash
python3 _okf_knowledge/kernel/okf.py tokens AGENTS.md
python3 _okf_knowledge/kernel/okf.py tokens AGENTS.md .github/copilot-instructions.md
python3 _okf_knowledge/kernel/okf.py tokens .cursor/rules .github/skills --ext md --ext mdc
python3 _okf_knowledge/kernel/okf.py tokens _okf_knowledge/standards --json
```

Uses **`tiktoken` (`cl100k_base`)** when that package is importable; otherwise the word/punct heuristic (and prints `method: heuristic`). For accurate counts on this repo:

```bash
python3 -m venv .venv
.venv/bin/pip install -r _okf_knowledge/kernel/requirements.txt
.venv/bin/python _okf_knowledge/kernel/okf.py tokens AGENTS.md
```

Directory walks default to common text extensions; pass `--all` for every file, or `--ext` to narrow. Skips `.git` / `node_modules` / venvs during descent.

## `okf.py compile`

**Use when:** you added/changed/removed concepts, links, or Prompt Cards and need fresh compiled caches.

Produces:

1. `index.json` — slim search index (v2 + inverted tokens)  
2. `prompt_cards.json` — card cache  
3. `kernel/src/graph.json` — nodes/edges (lookup hop-boost, pack `related:` edges, serve)  
4. Graph embed inside `okf-brain.html`

Also deletes legacy `context.toon` if present.

**Do not use when:** you only changed `docs/` human manuals or non-brain files — no need.

## `okf.py lint`

**Use when:** verifying vault health after mutations; CI gate.

Checks include (among others): frontmatter presence/type, link integrity, orphans, the **standards Prompt Card gate** (`DBG-308` / `DBG-309`), the `resource` field (`DBG-310` when the value is neither a URL nor a vault-absolute path, `DBG-311` when a `Reference` sets none), and the OKF v0.2 trust / lifecycle / provenance families:

| Code | Severity | Fires when |
| --- | --- | --- |
| `DBG-312` | warning | `generated` / `verified` is not a `{ by, at }` mapping, or the actor is missing |
| `DBG-313` | warning | An actor does not follow the §7 convention (`human:<name>` \| `process:<name>` \| `<agent>/<model>`) |
| `DBG-314` | warning | `status` is not `draft` \| `stable` \| `deprecated` |
| `DBG-315` | warning | `stale_after` is not `YYYY-MM-DD`, or the content is past it |
| `DBG-316` | warning | A `sources` entry is missing its required `resource` |
| `DBG-317` | **info** | A binding standard is unverified — no `verified` entry |

`DBG-312`–`DBG-316` fire only when a producer opted into one of these optional families and then got the shape wrong — absence is never an error. `DBG-317` is the inverse: it notes a binding standard nobody has confirmed.

Lint has three severities. The summary line reports all of them — `summary: 0 error(s), 0 warning(s), 5 info` — and `info` findings print as `INFO`, never fail the build, and do not stop lint from reporting `clean` (which means no errors **and** no warnings).

Success criterion for maintain checklist: **`0 error(s)`**. The errors are a missing/unparseable frontmatter block (`DBG-001` / `DBG-002`), a missing `type` (`DBG-301`), and a standard without a Prompt Card (`DBG-308`); everything else is a warning, except advisory `DBG-317`.

## `okf.py serve`

**Use when:** browsing the brain graph in a browser.

```bash
python3 _okf_knowledge/kernel/okf.py serve
# open http://localhost:8080/okf-brain.html
```

Typical APIs include compile/lint triggers for the UI (see script). Prefer this over opening `okf-brain.html` as a raw `file://` when embeds/fetch matter.

## `okf.py optimize`

**Use when:** Reference docs need normalization and folder indexes rebuilt, then graph refresh.

**MUST NOT** casually rewrite Playbooks/Systems/Concepts (see script header intent).

## `okf.py scrape`

**Use when:** pulling upstream documentation into `vault/` as `Reference` concepts (JIT).

It writes `resource: <url>` into the frontmatter of each document it creates, so the cached page always links back to its origin (and lint's `DBG-311` stays quiet). It also writes `generated: { by, at }`, `status: stable`, and a `sources` entry with a matching per-claim markdown footnote — provenance is frontmatter in v0.2, replacing the old `# Citations` body list. `verified` is deliberately left absent: a scrape is machine-fetched and nobody has confirmed it, so the card reads as `trust: unverified`.

Then follow [Maintenance](12-maintenance.md): indexes, cross-links, compile, lint, `log.md`.

## Recommended operator loops

### After editing vault or standards markdown

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

### Agent discovery during a task

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "your intent"
```

One command per task — it returns the capability line and the cards together.

### Explore visually

```bash
python3 _okf_knowledge/kernel/okf.py serve
```

Read-only: it serves `okf-brain.html` and `graph.json` over loopback and nothing else. There are no mutate endpoints and no authentication. To refresh what it shows, run `okf.py compile` (and `okf.py lint`) in a shell and reload the page.

The loopback-only bind is not authentication — it is content containment, because `graph.json` embeds full document bodies.

## Environment

| Variable | Effect |
| --- | --- |
| `OKF_VAULT_ROOT` | Override brain root (defaults to `_okf_knowledge/` next to `kernel/`) |

## Related

- [Compiled artifacts](07-compiled-artifacts.md)
- [Maintenance](12-maintenance.md)
- [Install & workflows](13-install-and-workflows.md)
