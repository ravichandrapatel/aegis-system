# 10. Kernel tools

[← Table of contents](README.md)

All scripts live in `_okf_knowledge/kernel/`. They are **stdlib Python** (no pip deps for core tools). Run them from the **package directory** (the folder that contains `AGENTS.md`).

```bash
cd /path/to/aegis-system
python3 _okf_knowledge/kernel/<script>.py …
```

## Catalog — when to use what

| Script | When to use | Primary outputs | Side effects |
| --- | --- | --- | --- |
| **`okf_lookup.py`** | Find concepts; build Prompt Pack | stdout hits / cards | Read-only |
| **`prompt_card.py`** | Extract cards for known paths | stdout cards | Read-only |
| **`graph_compiler.py`** | After any durable brain edit | `graph.json`, `index.json`, `prompt_cards.json`, HTML embed | Writes compiled artifacts |
| **`okf_lint.py`** | After edits; CI; pre-merge | console + `lint.json` | Writes `lint.json` |
| **`serve_vault.py`** | Local brain visualizer | HTTP on `:8080` | Serves files; may trigger compile/lint APIs |
| **`okf_common.py`** | Library only | n/a | Imported by other scripts |
| **`cache_optimizer.py`** | Normalize references / rebuild indexes | Updated reference indexes + compile | Rewrites reference-related indexes; runs compiler |
| **`registry_scraper.py`** | JIT fetch upstream docs into vault | New/updated vault markdown | Network + writes under vault |

## `okf_lookup.py`

Full detail: [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md).

**Use when:** you do not already know the concept path; you need ranked candidates or budgeted cards.

## `prompt_card.py`

**Use when:** paths are already known (e.g. from a previous lookup or a Profile’s required standards list).

**Do not use when:** you still need discovery — run lookup first.

## `graph_compiler.py`

**Use when:** you added/changed/removed concepts, links, or Prompt Cards and need fresh compiled caches.

Produces:

1. `graph.json` — nodes/edges (+ truncated content for UI)  
2. `index.json` — slim search index  
3. `prompt_cards.json` — card cache  
4. Updates embed inside `aegis-brain.html` when possible  

Also deletes legacy `context.toon` if present.

**Do not use when:** you only changed `docs/` human manuals or non-brain files — no need.

## `okf_lint.py`

**Use when:** verifying vault health after mutations; CI gate.

Checks include (among others): frontmatter presence/type, link integrity, orphans, and **standards Prompt Card gate** (`DBG-308` / `DBG-309`).

Success criterion for maintain checklist: **`0 error(s)`**.

## `serve_vault.py`

**Use when:** browsing the brain graph in a browser.

```bash
python3 _okf_knowledge/kernel/serve_vault.py
# open http://localhost:8080/aegis-brain.html
```

Typical APIs include compile/lint triggers for the UI (see script). Prefer this over opening `aegis-brain.html` as a raw `file://` when embeds/fetch matter.

## `okf_common.py`

Shared helpers: `VAULT_ROOT`, frontmatter parse, `load_vault`, link extraction, HTML inject helper. **Not a CLI.**

## `cache_optimizer.py`

**Use when:** Reference docs need normalization and folder indexes rebuilt, then graph refresh.

**MUST NOT** casually rewrite Playbooks/Systems/Concepts (see script header intent).

## `registry_scraper.py`

**Use when:** pulling upstream documentation into `vault/` as `Reference` concepts (JIT).

Then follow [Maintenance](13-maintenance.md): indexes, cross-links, compile, lint, `log.md`.

## Recommended operator loops

### After editing vault/standards/modules

```bash
python3 _okf_knowledge/kernel/graph_compiler.py
python3 _okf_knowledge/kernel/okf_lint.py
```

### Agent discovery during a task

```bash
python3 _okf_knowledge/kernel/okf_lookup.py "your intent"
python3 _okf_knowledge/kernel/okf_lookup.py --card "your intent"
```

### Explore visually

```bash
python3 _okf_knowledge/kernel/serve_vault.py
```

## Environment

| Variable | Effect |
| --- | --- |
| `OKF_VAULT_ROOT` | Override brain root (defaults to `_okf_knowledge/` next to `kernel/`) |

## Related

- [Compiled artifacts](08-compiled-artifacts.md)
- [Maintenance](13-maintenance.md)
- [Install & workflows](14-install-and-workflows.md)
