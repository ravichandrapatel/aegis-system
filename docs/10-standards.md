# 10. Standards (house law)

[← Table of contents](README.md)

Standards live in `_okf_knowledge/standards/`. They are **binding** governance documents. Agents resolve them via `okf.py pack` + Prompt Cards, not by pasting entire files into every turn.

## Shipped core standards (do not strip)

| File | One-line purpose |
| --- | --- |
| [`okf-prompt-injection.md`](../_okf_knowledge/standards/okf-prompt-injection.md) | **Rule #1 — Pack First**: pack/lookup before authoring; inject Prompt Cards only |
| [`okf-house-schema.md`](../_okf_knowledge/standards/okf-house-schema.md) | Required frontmatter + Prompt Card rules for durable docs |
| [`ide-context-guardrails.md`](../_okf_knowledge/standards/ide-context-guardrails.md) | No `@workspace` dumps; pack-first cards; `rg` over legacy search |
| [`simplicity-first.md`](../_okf_knowledge/standards/simplicity-first.md) | Laziness Ladder — the design lens applied **after** the pack |
| [`metadata-headers.md`](../_okf_knowledge/standards/metadata-headers.md) | Required metadata on new kernel Python files/functions |

`AGENTS.md` binds non-trivial work to Rule #1 (Pack First). `okf.py lint` **fails** if any `standards/*` concept lacks a non-empty `## Prompt Card`.

## When to read which standard

| Situation | Open |
| --- | --- |
| Assembling generation context / Prompt Pack | OKF Prompt Injection (Rule #1) |
| Authoring or ingesting a durable document | OKF House Schema |
| Working inside Copilot / Cursor and worried about context bloat | IDE Context Guardrails |
| Choosing between designs / folder layouts / abstractions | Simplicity First |
| Adding a new kernel script or code surface | Metadata Headers |
| Writing a **new** house policy | Create a new `standards/*.md` (see below) |

## Rule #1 — Pack First (summary)

There is exactly one numbered rule. Non-trivial work starts with:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<task keywords>"
```

| MUST | FORBIDDEN |
| --- | --- |
| Build the Prompt Pack from `## Prompt Card` sections | Paste compiled artifacts / full standards into generation by default |
| Keep cards slim (≤ ~150 tokens each) | “Load the whole OKF brain” as default authoring strategy |
| Run the pack **once per task** | Re-querying variations after an empty pack |
| Treat an empty pack as a finished search | Claiming compliance without having run a pack |
| Reach further by following a card's `related:` / `source:` edge | Re-packing with reworded queries instead of traversing |

Pack budget: **max 8 cards**, **~1200 token** budget — both enforced by `okf.py` (`--max-cards` / `--budget`), with an oversized single card truncated to fit.

> The Prompt Injection standard’s card text may mention a tighter ~400-token SHOULD for a single generation turn. Treat the kernel defaults as the orchestration budget; keep individual cards small either way.

## Simplicity First — the design lens (summary)

**Not a numbered rule.** It is the lens applied *after* the pack, when several approaches would all work. Laziness Ladder (lowest rung that still works):

1. Do nothing new (reuse)  
2. Edit one file  
3. Add one small file  
4. Add tooling (when pain repeats)  
5. Add abstraction (**last**)

Applies to vault structure **and** code diffs.

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
2. Create `standards/<name>.md` with frontmatter including `tags: [standard, …]`.  
3. Add normative MUST/SHOULD/FORBIDDEN sections.  
4. Add a non-empty `## Prompt Card`.  
5. Update `standards/index.md`, cross-links, `log.md`.  
6. Run `okf.py compile` + `okf.py lint`.

Full procedure: [Maintenance](12-maintenance.md).

## Conflict resolution involving standards

> **Convention, not kernel behavior.** There is no `owns` / `priority` frontmatter arbitration — those fields do not exist in the schema and lint never checks them.

If two standards overlap, `AGENTS.md` resolves it by reasoning, not by code:

1. At plan time, the OKF standard outranks a conflicting preference — note the correction and continue.  
2. At execution time, a conflict with the approved plan **fails closed** (`PENDING_APPROVAL` or `BLOCKED`).  
3. Never guess between two contradictory standards — surface the contradiction and fix one of the documents.

See [Protocol](06-protocol-routing.md).

## Related

- [Frontmatter schema](05-frontmatter-schema.md)
- [Lookup & Prompt Cards](08-lookup-and-prompt-cards.md)
- [`standards/index.md`](../_okf_knowledge/standards/index.md)
