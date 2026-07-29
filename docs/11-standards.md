# 11. Standards (house law)

[← Table of contents](README.md)

Standards live in `_okf_knowledge/standards/`. They are **binding** governance documents. Agents resolve them via lookup + Prompt Cards, not by pasting entire files into every turn.

## Shipped core standards (do not strip)

| File | Rule | One-line purpose |
| --- | --- | --- |
| [`simplicity-first.md`](../_okf_knowledge/standards/simplicity-first.md) | **Rule #1** | Laziness Ladder — simplest solution that works |
| [`okf-prompt-injection.md`](../_okf_knowledge/standards/okf-prompt-injection.md) | **Rule #2** | Inject Prompt Cards only; never dump the brain |
| [`metadata-headers.md`](../_okf_knowledge/standards/metadata-headers.md) | Headers | Required metadata on new files/functions/classes |

`AGENTS.md` Path A binds generation to Rule #2. `okf.py lint` **fails** if any `standards/*` concept lacks a non-empty `## Prompt Card`.

## When to read which standard

| Situation | Open |
| --- | --- |
| Choosing between designs / folder layouts / abstractions | Rule #1 Simplicity First |
| Assembling generation context / Prompt Pack | Rule #2 Prompt Injection |
| Adding a new kernel script or code surface | Metadata Headers |
| Writing a **new** house policy | Create a new `standards/*.md` (see below) |

## Rule #1 — Simplicity First (summary)

Laziness Ladder (lowest rung that still works):

1. Do nothing new (reuse)  
2. Edit one file  
3. Add one small file  
4. Add tooling (when pain repeats)  
5. Add abstraction (**last**)

Applies to vault structure **and** code diffs.

## Rule #2 — OKF Prompt Injection (summary)

| MUST | FORBIDDEN |
| --- | --- |
| Build Prompt Pack from `## Prompt Card` sections | Paste compiled artifacts / full standards into generation by default |
| Keep cards slim (≤ ~150 tokens each) | “Load the whole Aegis brain” as default authoring strategy |
| Prefer lookup → `--card` | Treating multi-turn fix loops as better than a one-shot card |

Protocol pack budget (`AGENTS.md` §4.2): **max 8 cards** (hard), target ≈**1200** tokens (guidance), with deterministic eviction.

> The Prompt Injection standard’s card text may mention a tighter ~400-token SHOULD for a single generation turn. Treat **AGENTS.md §4.2 as the orchestration budget**; keep individual cards small either way.

## Metadata Headers (summary)

New files need:

```text
file_name, description, version, authors
```

New functions/classes need:

```text
intent, input, output, role, side_effects
```

Match existing kernel header style (snake_case field names).

## Adding a new standard

1. Confirm it is **law**, not a how-to (else Playbook/Concept in vault).  
2. Create `standards/<name>.md` with frontmatter including `tags: [standard, …]`, `owns`, `priority`.  
3. Add normative MUST/SHOULD/FORBIDDEN sections.  
4. Add a non-empty `## Prompt Card`.  
5. Update `standards/index.md`, cross-links, `log.md`.  
6. Run `okf.py compile` + `okf.py lint`.

Full procedure: [Maintenance](13-maintenance.md).

## Conflict resolution involving standards

If two standards overlap:

1. Prefer the document whose `owns` claims the domain.  
2. Else higher `priority` wins.  
3. Else identical `owns`+`priority` → **fail closed** (exit 1).

See [Protocol](06-protocol-routing.md).

## Related

- [Frontmatter schema](05-frontmatter-schema.md)
- [Lookup & Prompt Cards](09-lookup-and-prompt-cards.md)
- [`standards/index.md`](../_okf_knowledge/standards/index.md)
