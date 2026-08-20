---
type: Concept
title: Python Naming
description: Binding single-style identifier rules for the OKF runtime package (PEP 8 snake_case).
tags: [standard, python, naming, pep8, conventions, code-quality]
generated: { by: okf-agent/cursor, at: 2026-08-21T00:00:00Z }
status: stable
pack_force_when: [python naming, snake_case, UPPER_SNAKE, variable style, naming lint]
---

# Python Naming

**Binding** for `_okf_knowledge/kernel/okf/**/*.py` and `_okf_knowledge/kernel/okf.py`. Enforced by `okf.py lint` (`DBG-320`, `DBG-321`). Domain code outside this package SHOULD follow the same rules.

## One style per name

Every identifier is **exactly one** of:

| Style | Pattern | Used for |
| --- | --- | --- |
| `lower_snake` | `_?[a-z][a-z0-9_]*` | modules, files, functions, params, locals |
| `UPPER_SNAKE` | `_?[A-Z][A-Z0-9_]*` | module constants only |
| `CapWords` | `_?[A-Z][A-Za-z0-9]*` (no `_`) | classes and type aliases only |

**Exception:** stdlib overrides that the runtime requires (e.g. `BaseHTTPRequestHandler.do_GET`) keep the upstream spelling.

**Forbidden**

- Mixing styles in one name (`MaxCards`, `VAULT_root`, `parseHTML`)
- Product prefixes on identifiers (`okf_*`, `OKF_*`, `kernel_*`, `KERNEL_*`) — the package import `okf` is fine; prefixes on *variables* are not
- `camelCase` functions or locals

Schema keys in frontmatter (e.g. `okf_version`) are document fields, not Python identifiers — leave them alone.

## Examples

```python
# good
VAULT_ROOT = Path("...")
DEFAULT_MAX_CARDS = 8
entry_script = brain / "okf.py"

class IndexEntry:
    def score_hit(self, query: str) -> int: ...

# bad
okf_config = {}       # product prefix
KERNEL_DIR = ...      # product prefix
maxCards = 8          # camelCase
parseHTML = ...         # mixed
```

## Files

Python modules and package data files use `lower_snake` (e.g. `paths.py`, `brain.html`).

## Prompt Card

```text
OKF runtime Python: one style per name — lower_snake (funcs/locals/files),
UPPER_SNAKE (constants), CapWords (classes/types only). Never mix; never okf_/kernel_ prefixes on identifiers. Lint: DBG-320 style, DBG-321 prefix.
```

# Related

- [Metadata Headers](/standards/metadata-headers.md) — file/function header fields
- [Simplicity First](/standards/simplicity-first.md)
- [OKF House Schema](/standards/okf-house-schema.md)
