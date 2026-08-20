---
name: okf-discover
description: Detailed capability probe — only when the pack caps line is degraded
---

Usually unnecessary: `okf.py pack` already prints a `caps:` line. Follow the agent skill [okf-discover](../skills/okf-discover/SKILL.md).

```bash
python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
```
