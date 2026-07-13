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
# file_name: registry_scraper.py
# description: JIT fetch of upstream docs into OKF Reference concepts.
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

# Related

- [Simplicity First](/standards/simplicity-first.md)
