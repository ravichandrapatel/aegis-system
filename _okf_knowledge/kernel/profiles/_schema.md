---
type: Profile
title: [Dynamic Role Name]
description: [One-sentence description of the persona's objective]
tags: [profile, dynamic, role-specific-tags]
last_modified: [ISO-8601 Timestamp]
status: active
---

# Profile: [Dynamic Role Name]

## 1. Profile Objective
[Define the scope, boundaries, and primary goal of this persona. What are they authorized to do?]

## 2. Dynamic Capabilities (RBAC)

### 2.1 Authorized Intents
* `[Intent 1 - e.g., CREATE, REVIEW, OPERATE]`
* `[Intent 2]`

### 2.2 Execution Modes
* `[advisory | generate | enforce]`
* *(Specify if any mode is strictly PROHIBITED for this role)*

### 2.3 Required Core Modules
* `kernel/modules/[module-name].md`
* `kernel/modules/[module-name].md`
* *(Aegis will HALT if these are missing during the Capability Check)*

### 2.4 Enforced Standards
* `standards/[standard-name].md`
* `standards/[standard-name].md`
* *(Governance rules that strictly apply to this role's output)*