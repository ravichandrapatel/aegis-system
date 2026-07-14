---
type: Concept
title: Metadata Headers
description: Required metadata blocks on every new file, function, and class across all languages.
tags: [standard, code-quality, documentation, conventions]
timestamp: 2026-07-13T14:30:00Z
status: active
---

Every new file, function, and class MUST carry a metadata block. This makes code
self-describing for both humans and agents.

# File header

Fields: `file_name`, `description`, `version`, `authors` (snake_case).

```python
# file_name: okf.py
# description: Single-file Aegis OKF kernel (lookup, compile, lint, ...).
# version: 0.1.0
# authors: contributors
```

# Function / class header

Fields: `intent`, `input`, `output`, `role`, `side_effects` (snake_case).

```python
def slugify(text: str) -> str:
    """
    intent: Turn a free-text query into a safe filename slug.
    input: text — arbitrary user query string.
    output: lowercase kebab-case slug.
    role: pure helper.
    side_effects: none.
    """
```

## Prompt Card

```text
Metadata MUST on new files: file_name, description, version, authors.
On new functions/classes: intent, input, output, role, side_effects.
Snake_case field names; match existing kernel header style.
```

# Related

- [Simplicity First](/standards/simplicity-first.md)
