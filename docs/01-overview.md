# 1. Overview

[← Table of contents](README.md)

## What Aegis is

**Aegis** is a portable **Engineering Control Plane** for AI coding agents. It orchestrates reviews, enforces governance, generates infrastructure/config, and executes safe state mutations with a hard standard: **Zero Downtime, Zero Surprises.**

It ships as one folder containing:

1. **`AGENTS.md`** — immutable protocol (how Aegis thinks, routes intent, budgets context, and formats output).
2. **`_okf_knowledge/`** — the **Aegis Brain**: curated OKF markdown (what Aegis knows) plus small Python **kernel** tools (how to find, lint, and compile that knowledge).

Together they zip into an IDE agents/skills directory and travel with the team. No database and no cloud dependency are required for core routing.

## What Aegis is not

| Not this | Why that matters |
| --- | --- |
| An AST / tree-sitter **code indexer** | Tools like okf-generator map *code symbols*. Aegis stores **operational and policy knowledge**. |
| A vector RAG store | Default lookup is **deterministic** over frontmatter (title, tags, path, type) — not embeddings. |
| A replacement for project source | Application repos stay untouched; the brain is a **sibling knowledge package**. |
| A dump of the whole vault into the LLM | Agents **lookup → Prompt Card**, never paste compiled artifacts (`index.json`, graph embeds) or entire standards by default. |

## Design goal (one sentence)

**Find the right knowledge cheaply, inject only what is needed to generate or validate, keep the brain reviewable and maintainable.**

## The two roots (mental model)

| Root | Authority | Mutability | Typical consumer |
| --- | --- | --- | --- |
| `AGENTS.md` | Binding control-plane contract | Rare (protocol bumps) | Agents (always), humans (onboarding) |
| `_okf_knowledge/` | Knowledge + tools | Frequent (ingest / maintain) | Agents (lookup/cards), humans (PRs), CI (lint) |

If you change *how* Aegis must behave (routing, budgets, report schemas), edit **`AGENTS.md`**.  
If you change *what* Aegis knows (EKS facts, playbooks, house rules), edit the **brain** via the [maintenance playbook](13-maintenance.md).

## End-to-end flow (high level)

```
User intent (CREATE / REVIEW / DEPLOY / MAINTAIN / …)
        │
        ▼
Load Profile (kernel/profiles/)
        │
        ▼
Capability check (required modules/vendors/standards present?)
        │
        ▼
Context expansion (typed graph traversal + lookup)
        │
        ▼
Assemble Prompt Pack (≤ 8 cards hard; target ≈1200 tokens)
        │
        ▼
Path A Generation  |  Path B Validation  |  Path C Execution
        │
        ▼
Structured report + Status Footer (exit code, risk, evidence grades)
```

Details: [Protocol & routing](06-protocol-routing.md), [Pipelines & outputs](12-pipelines-and-outputs.md).

## Core principles baked into the package

| Rule | Where defined | Practical effect |
| --- | --- | --- |
| **Rule #1 — Simplicity First** | `standards/simplicity-first.md` | Prefer the smallest change that works (Laziness Ladder). |
| **Rule #2 — Prompt Cards only** | `standards/okf-prompt-injection.md` | Generation context gets slim cards, not encyclopedia dumps. |
| **Metadata headers** | `standards/metadata-headers.md` | New kernel/code files carry self-describing headers. |
| **Brain mutations follow one playbook** | `AGENTS.md` §1.2 + `maintain-aegis-system.md` | No ad-hoc invent-a-folder ingest. |

## Where to go next

| If you are… | Read next |
| --- | --- |
| New to the package | [Package layout](02-package-layout.md) → [Brain zones](03-brain-zones.md) |
| Adding knowledge | [Document types](04-document-types.md) → [Maintenance](13-maintenance.md) |
| Running tools | [Kernel tools](10-kernel-tools.md) |
| Understanding compiled JSON | [Compiled artifacts](08-compiled-artifacts.md) |
