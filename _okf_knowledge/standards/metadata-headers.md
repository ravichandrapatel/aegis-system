---
type: Concept
title: Metadata Headers
description: Required metadata blocks on new okf package modules and house scripts.
tags: [standard, code-quality, documentation, conventions, python]
generated: { by: okf-agent/cursor, at: 2026-07-28T00:30:00Z }
status: stable
---

# Metadata Headers

**Scope:** new/edited files under `_okf_knowledge/kernel/okf/` and other house Python tooling. Domain YAML/code follows this repo’s domain standards when present.

**Identifier style** is binding under [Python Naming](/standards/python-naming.md) and enforced by `okf.py lint` — do not invent a second convention here.

## File header

```python
# file_name: okf.py
# description: Thin CLI caller for the OKF runtime package.
# version: 1.3.0
# authors: contributors
```

Header keys are `lower_snake` only (`file_name`, not `FILE_NAME`).

## Function / class docstring fields

`intent`, `input`, `output`, `role`, `side_effects` (snake_case) — match existing package style.

## Prompt Card

```text
House Python headers: file_name/description/version/authors (lower_snake keys).
Docstrings: intent, input, output, role, side_effects.
Identifier style: standards/python-naming.md (lint DBG-320/321).
```

# Related

- [Python Naming](/standards/python-naming.md)
- [Simplicity First](/standards/simplicity-first.md)
- [OKF House Schema](/standards/okf-house-schema.md)
