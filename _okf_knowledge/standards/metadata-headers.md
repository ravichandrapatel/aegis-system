---
type: Concept
title: Metadata Headers
description: Required metadata blocks on new kernel Python modules and house scripts.
tags: [standard, code-quality, documentation, conventions, python]
timestamp: 2026-07-28T00:30:00Z
status: active
---

# Metadata Headers

**Scope:** new/edited files under `_okf_knowledge/kernel/` and other house Python tooling. Domain YAML/code follows this repo’s domain standards when present.

## File header

```python
# file_name: okf.py
# description: Thin CLI caller for the Aegis OKF kernel.
# version: 1.3.0
# authors: contributors
```

## Function / class docstring fields

`intent`, `input`, `output`, `role`, `side_effects` (snake_case) — match existing kernel style.

## Prompt Card

```text
Kernel/house Python: file headers (file_name, description, version, authors).
New functions: intent, input, output, role, side_effects. Domain files: follow local standards.
```

# Related

- [Simplicity First](/standards/simplicity-first.md)
- [OKF House Schema](/standards/okf-house-schema.md)
