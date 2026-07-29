---
type: Profile
title: Profile schema
description: Template for optional kernel/profiles — objective, intents, modes, required vault/standards lookup paths. Not a runtime Module/Vendor gate.
tags: [profile, schema, template, persona, rbac]
timestamp: 2026-07-18T02:45:00Z
status: active
---

# Profile schema

Template for optional capability profiles under `kernel/profiles/`. Copy this file; replace placeholders. Profiles are **not** a runtime Module/Vendor gate — domain knowledge loads via OKF lookup.

## 1. Profile objective

Define the scope, boundaries, and primary goal of this persona. What are they authorized to do?

## 2. Dynamic capabilities (RBAC)

### 2.1 Authorized intents

* Example: `CREATE`, `REVIEW`, `OPERATE`
* Add intents this role may run

### 2.2 Execution modes

* One or more of: `advisory` | `generate` | `enforce`
* Note any mode that is strictly PROHIBITED for this role

### 2.3 Required vault / standards (lookup)

* Example paths: `vault/concepts/extending-aegis.md`, `vault/playbooks/maintain-aegis-system.md`
* Example standard: `standards/simplicity-first.md`, `standards/okf-prompt-injection.md`
* Documented for future Profile use — kernel does not enforce missing paths today

### 2.4 Enforced standards

* Example: `standards/simplicity-first.md`, `standards/okf-prompt-injection.md`
* Governance rules that strictly apply to this role's output

## Prompt Card

```text
Optional Profile under kernel/profiles/: copy this template; set objective,
authorized intents, modes (advisory|generate|enforce), required vault/standards
paths, enforced standards. Not a Module/Vendor runtime gate — load domain via OKF lookup.
```

## Related

- Control plane: [AGENTS.md](/AGENTS.md)
- Maintenance: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Prompt rules: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Extending: [Extending Aegis](/vault/concepts/extending-aegis.md)
