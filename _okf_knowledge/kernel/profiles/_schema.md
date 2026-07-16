---
type: Profile
title: Profile schema
description: One-sentence description of the persona's objective — template for optional kernel/profiles.
tags: [profile, schema, template]
last_modified: 2026-07-17T03:28:00Z
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

* Example paths: `vault/concepts/github-actions.md`, `vault/systems/gha-reusable-actions-workflows.md`
* Example standard: `standards/gha-spvs-yaml.md`
* Documented for future Profile use — kernel does not enforce missing paths today

### 2.4 Enforced standards

* Example: `standards/simplicity-first.md`, `standards/okf-prompt-injection.md`
* Governance rules that strictly apply to this role's output

## Related

- Control plane: [AGENTS.md](/AGENTS.md)
- Maintenance: [Maintain aegis-system](/vault/playbooks/maintain-aegis-system.md)
- Prompt rules: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
- Extending: [Extending Aegis](/vault/concepts/extending-aegis.md)
