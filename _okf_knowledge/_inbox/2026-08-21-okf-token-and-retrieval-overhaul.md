# OKF token + retrieval overhaul (Rung 1 write-back)

**Date:** 2026-08-21
**Trigger:** non-trivial change close-out + root cause found + lookup gap
**Status:** untriaged — promote via [maintain playbook](../vault/playbooks/maintain-okf-system.md)

## Why this happened

The user reported OKF was "wasting too many tokens and slow" with Copilot and Cursor. Measurement confirmed it, and the cause split cleanly in two.

**Standing cost.** Every turn carried ~5,550 tokens of always-applied rules before the user's question was even read. Roughly half was dead weight: a parent workspace rule describing a `knowledge/` tree, a `context.toon` index, and three `kernel/scripts/*.py` tools — none of which exist anywhere on this machine. A second parent rule repeated the same phantom toolchain. A third was byte-for-byte duplicated between the workspace and the global Cursor config, so it was billed twice.

**Per-task cost.** The protocol mandated Capability Discovery, then a Prompt Pack, as separate steps, each needing its own skill file read. That is 4 LLM round trips before any work begins — and round trips, not tokens, dominate wall-clock latency. The kernel itself is fast (~130 ms).

## Root causes worth remembering

1. **Documentation drift is a token tax, not just a correctness problem.** Rules describing tools that do not exist still get billed on every single turn, and they actively induce hallucination: an agent told to run `toon_compiler.py` will try, fail, and improvise.

2. **Substring matching in a force-include mechanism is a precision disaster.** `pack_force_when: [tab]` fired on "table", "stable", and "portable"; `deploy` fired on "deployment". Because forced cards enter at score 10,000, a false positive did not merely add noise — it outranked every legitimate result. The lesson generalizes: any rule that *overrides* ranking must match far more strictly than one that merely *contributes* to it.

3. **Merging a combined token bag into per-field bags destroys field weighting.** Description tokens were unioned into the title and id bags, so a word appearing only in a description scored as an exact title hit. "how do I bake a cake" scored 83 against an unrelated concept. If fields carry different weights, their token bags must stay separate.

4. **"Always return the best match" is wrong for authoritative retrieval.** A search engine returning a weak result costs the user a glance. A knowledge system injecting a weak result as a *binding card* actively overrides the model's own correct judgement. Below a relevance floor, returning nothing is strictly better.

5. **A self-referential vault makes the protocol pure overhead.** All 9 concepts describe OKF itself. For any real engineering question the pack is empty, so Rule #1 costs a command and returns nothing. The protocol only pays for itself once the vault holds domain knowledge the repo actually argues about.

## Durable rules extracted

- Keyword lists that force retrieval must use distinctive multi-word phrases, never common English words. Prefer `extend okf` over `extend`, `cognitive bundle` over `bundle`.
- An empty pack must be documented as a *valid terminal answer*. Without that, agents burn turns rewording queries until something matches — the exact failure the relevance floor was added to prevent.
- Capability probes belong inline with the work they gate. Discovery folded into `pack` removed 3 round trips at no information loss, because capabilities do not change mid-session.
- Any file duplicated across two tool ecosystems (`.cursor/` and `.github/`) must be generated from one source with a CI drift gate. Manual parity always decays.
- Egress to an external LLM needs a secret scan. The kernel already scanned content coming *into* the vault via `scrape`, but `enrich` sent whole documents *out* with no check. **Superseded:** `enrich` was removed entirely rather than guarded — deleting the feature deleted the whole SSRF and credential surface with it. When a feature is unused, removing it beats hardening it.
- Authentication is a symptom, not a goal. `serve` needed a token only because it exposed `/api/compile`, which rewrote repository files. Making the server read-only removed the requirement instead of managing it. Loopback binding stayed, but as *content containment* for `graph.json` (which embeds full document bodies), not as authentication.

## Open items not addressed

- **The vault still has no domain knowledge.** This is the single highest-value remaining gap and cannot be fixed mechanically — it needs real standards from the repos OKF governs.
- Prose-only contracts (Status Footer, evidence grades, report schemas) are now labelled as unenforced conventions, but nothing verifies agents follow them.
- `docs/ADR.md` retains historical rows that still use the old "Rule #2" numbering; left intact deliberately since a changelog should not be rewritten.

## Related

- [OKF Prompt Injection](../standards/okf-prompt-injection.md)
- [IDE Context Guardrails](../standards/ide-context-guardrails.md)
- [Extending OKF](../vault/concepts/extending-okf.md)
- [OKF Capability Discovery](../vault/concepts/okf-capability-discovery.md)
