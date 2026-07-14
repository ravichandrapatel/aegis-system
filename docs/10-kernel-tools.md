# 10. Kernel tools

[← Table of contents](README.md)

The kernel is a **single stdlib-Python script** — `_okf_knowledge/kernel/okf.py` — with one subcommand per operation (no pip deps). Run it from the **package directory** (the folder that contains `AGENTS.md`).

```bash
cd /path/to/aegis-system
python3 _okf_knowledge/kernel/okf.py <subcommand> …
```

## Catalog — when to use what

| Subcommand | When to use | Primary outputs | Side effects |
| --- | --- | --- | --- |
| **`okf.py lookup`** | Find concepts; build Prompt Pack | stdout hits / cards | Read-only |
| **`okf.py card`** | Extract cards for known paths | stdout cards | Read-only |
| **`okf.py compile`** | After any durable brain edit | `graph.json`, `index.json`, `prompt_cards.json`, HTML embed | Writes compiled artifacts |
| **`okf.py lint`** | After edits; CI; pre-merge | console + `lint.json` | Writes `lint.json` |
| **`okf.py serve`** | Local brain visualizer | HTTP on `:8080` | Serves files; may trigger compile/lint APIs |
| **`okf.py optimize`** | Normalize references / rebuild indexes | Updated reference indexes + compile | Rewrites reference-related indexes; runs compiler |
| **`okf.py enrich`** | Fill missing description/tags/Prompt Card via LLM | Report; `--write` edits concepts | Network (LLM); `--write` edits vault files |
| **`okf.py scrape`** | JIT fetch upstream docs into vault | New/updated vault markdown | Network + writes under vault |

## `okf.py lookup`

Full detail: [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md).

**Use when:** you do not already know the concept path; you need ranked candidates or budgeted cards.

## `okf.py card`

**Use when:** paths are already known (e.g. from a previous lookup or a Profile’s required standards list).

**Do not use when:** you still need discovery — run lookup first.

## `okf.py compile`

**Use when:** you added/changed/removed concepts, links, or Prompt Cards and need fresh compiled caches.

Produces:

1. `graph.json` — nodes/edges (+ truncated content for UI)  
2. `index.json` — slim search index  
3. `prompt_cards.json` — card cache  
4. Updates embed inside `aegis-brain.html` when possible  

Also deletes legacy `context.toon` if present.

**Do not use when:** you only changed `docs/` human manuals or non-brain files — no need.

## `okf.py lint`

**Use when:** verifying vault health after mutations; CI gate.

Checks include (among others): frontmatter presence/type, link integrity, orphans, and **standards Prompt Card gate** (`DBG-308` / `DBG-309`).

Success criterion for maintain checklist: **`0 error(s)`**.

## `okf.py serve`

**Use when:** browsing the brain graph in a browser.

```bash
python3 _okf_knowledge/kernel/okf.py serve
# open http://localhost:8080/aegis-brain.html
```

Typical APIs include compile/lint triggers for the UI (see script). Prefer this over opening `aegis-brain.html` as a raw `file://` when embeds/fetch matter.

## `okf.py optimize`

**Use when:** Reference docs need normalization and folder indexes rebuilt, then graph refresh.

**MUST NOT** casually rewrite Playbooks/Systems/Concepts (see script header intent).

## `okf.py enrich`

**Use when:** lookup quality degrades because concepts lack a `description`, useful `tags`, or a `## Prompt Card` (the three fields `okf.py lookup` ranks and injects). Typical after bulk ingest.

```bash
# Report gaps (no network, exit 1 if gaps exist — CI-friendly)
python3 _okf_knowledge/kernel/okf.py enrich

# Fill gaps via an OpenAI-compatible endpoint
export OKF_LLM_BASE_URL=http://localhost:11434/v1   # or https://api.openai.com/v1
export OKF_LLM_API_KEY=sk-...                        # optional for local models
export OKF_LLM_MODEL=llama3.1                        # or gpt-4o-mini, etc.
python3 _okf_knowledge/kernel/okf.py enrich --write [--only playbooks] [--limit 5]
```

Gap-fill only and idempotent: existing fields are never overwritten, tags are merged, cards are inserted before `# Related`, and LLM output is sanitized and clamped (card ≤ 600 chars) before any write. Follow with the compile + lint loop.

**Do not use when:** the gap is judgment content (steps, ownership tables) — write that by hand per the maintain playbook.

## `okf.py scrape`

**Use when:** pulling upstream documentation into `vault/` as `Reference` concepts (JIT).

Then follow [Maintenance](13-maintenance.md): indexes, cross-links, compile, lint, `log.md`.

## Recommended operator loops

### After editing vault/standards/modules

```bash
python3 _okf_knowledge/kernel/okf.py compile
python3 _okf_knowledge/kernel/okf.py lint
```

### Agent discovery during a task

```bash
python3 _okf_knowledge/kernel/okf.py lookup "your intent"
python3 _okf_knowledge/kernel/okf.py lookup --card "your intent"
```

### Explore visually

```bash
python3 _okf_knowledge/kernel/okf.py serve
```

## Environment

| Variable | Effect |
| --- | --- |
| `OKF_VAULT_ROOT` | Override brain root (defaults to `_okf_knowledge/` next to `kernel/`) |
| `OKF_LLM_BASE_URL` / `OKF_LLM_API_KEY` / `OKF_LLM_MODEL` | Endpoint for `okf.py enrich --write` (OpenAI-compatible) |

## Related

- [Compiled artifacts](08-compiled-artifacts.md)
- [Maintenance](13-maintenance.md)
- [Install & workflows](14-install-and-workflows.md)
