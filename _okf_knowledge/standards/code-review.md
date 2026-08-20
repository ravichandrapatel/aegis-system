---
type: Concept
title: Code Review
description: Binding bar, dimensions, comment protocol, and decision states for reviewing changes.
tags: [standard, code-review, quality, devops, process]
generated: { by: okf-agent/cursor, at: 2026-08-21T02:45:00Z }
status: stable
pack_force_when: [code review, review a pr, pull request review, reviewer, lgtm, review comment, nitpick]
---

# Code Review

**Binding** for every human or agent review of a change in this workspace: application code, infrastructure, pipelines, and vault content. Objective checks belong to [Code Quality Gates](/standards/code-quality-gates.md); this standard covers the judgement a gate cannot make.

Adapted from Google's [Engineering Practices](https://google.github.io/eng-practices/review/) (`google/eng-practices`, ~21k stars, CC-BY 3.0), [thoughtbot/guides](https://github.com/thoughtbot/guides/tree/master/code-review) (~10k stars), and [Conventional Comments](https://conventionalcomments.org).

## The bar

> Approve once the change **definitely improves the overall code health** of the system, even if it is not perfect.

There is no perfect code, only better code. Reviewers seek continuous improvement, not polish. A reviewer **MUST NOT** block on personal preference; a reviewer **MUST** block on a demonstrable harm to health, correctness, or blast radius.

| Rule | Value |
| --- | --- |
| First response | ≤ 1 business day (at a natural break, not mid-focus) |
| Target change size | ≤ 200 lines; **hard ceiling 400** — above that, ask for a split |
| Style authority | The style guide / linter, never the reviewer's taste |
| Unresolved nits | Approve with comments rather than round-trip |

If a change cannot be split, still review the design and return it quickly. The goal of every response is to **unblock the author** without lowering the bar.

## Dimensions — in priority order

Review **top-down**; a design problem makes every line below it moot.

1. **Design** — does the change belong here, and does it integrate with the system?
2. **Blast radius & rollback** — what breaks if this is wrong, and how is it undone? (**MUST** be answerable for anything touching infrastructure, pipelines, data, or auth.)
3. **Functionality** — does it do what the author intended, including edge cases, concurrency, and failure paths?
4. **Security** — secrets, least privilege, untrusted input, supply-chain pinning. See [Code Quality Gates](/standards/code-quality-gates.md).
5. **Complexity** — too complex to understand quickly, or over-engineered for a speculated future need?
6. **Tests** — present, correct, and able to actually fail; tests are maintained code too.
7. **Naming & comments** — names communicate; comments explain *why*, not *what*.
8. **Consistency & style** — style guide wins; otherwise match surrounding code.
9. **Documentation** — updated when build, run, interface, or release behaviour changed.
10. **Observability & cost** — for production changes: is the change visible in logs/metrics, and what does it cost?

Read **every line** you were asked to review. If a part is outside your competence (crypto, privacy, kernel), say so and name the reviewer who should cover it — do not silently approve it.

## Comment protocol

Every comment uses a [Conventional Comments](https://conventionalcomments.org) label so intent and blocking status are unambiguous and greppable:

```text
<label> [decorations]: <subject>

[discussion — the why and the next step]
```

| Label | Use for |
| --- | --- |
| `issue` | A real defect. **SHOULD** be paired with a `suggestion` |
| `suggestion` | A concrete improvement, ideally as a patch |
| `question` | A possible concern you are unsure about |
| `todo` | Small, necessary, uncontroversial change |
| `nitpick` | Trivial preference — **always** non-blocking |
| `praise` | Something done well — leave at least one, never false |
| `thought` / `note` / `chore` | Non-blocking idea, FYI, or process step |

Decorations: `(blocking)`, `(non-blocking)`, `(if-minor)`, plus domain tags such as `(security)`, `(test)`. **Default in this workspace: comments are non-blocking unless decorated `(blocking)`.**

**MUST**

- Address the code, never the author ("this function", not "you").
- Collapse repeated style offences into **one** comment plus a linter suggestion.
- Explain the *why*; a verdict with no reasoning is not a review.

**FORBIDDEN**

- Debating a style rule inside the review — apply it, then open an issue against the rule.
- Blocking on taste, hypothetical future requirements, or unrelated pre-existing debt (file a follow-up instead).
- Agent reviews that assert a violation without citing the file/line or the standard.

## Decision

Close every review with exactly one:

| Decision | Meaning |
| --- | --- |
| **Approved** | Improves code health. Non-blocking comments may remain open |
| **Manual Intervention** | Blocking findings the author can resolve — each one actionable |
| **Blocked** | Design, security, or blast-radius problem; needs a different approach or an owner decision |

Grade the evidence behind each finding: `verified` > `observed` > `provided` > `inferred`. Never ship `assumed` as a production finding. A high-risk fix routes through the `mutation-gate` skill before it is applied.

## Prompt Card

```text
Approve when the change improves overall code health — not when it is perfect. Respond ≤1 business day; ≤200 LOC target, 400 hard ceiling, else request a split.
Review top-down: design > blast radius/rollback > functionality > security > complexity > tests > naming > style > docs > observability/cost.
Comment with Conventional Comments labels (issue/suggestion/question/todo/nitpick/praise); non-blocking unless "(blocking)". Style rules come from the linter, never reviewer taste.
Close as Approved | Manual Intervention | Blocked, each finding citing file:line + standard.
```

# Related

- Gates: [Code Quality Gates](/standards/code-quality-gates.md)
- Simplicity: [Simplicity First](/standards/simplicity-first.md)
- Schema: [OKF House Schema](/standards/okf-house-schema.md)
- Retrieval: [OKF Prompt Injection](/standards/okf-prompt-injection.md)
