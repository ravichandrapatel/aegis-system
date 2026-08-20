# OKF spec alignment — traversal and `resource` (Rung 1 write-back)

**Date:** 2026-08-21
**Trigger:** user-corrected fact + root cause found + non-trivial change close-out
**Status:** untriaged — promote via [maintain playbook](../vault/playbooks/maintain-okf-system.md)

## Why this happened

The user supplied the actual definition of OKF — Google Cloud's [Open Knowledge Format](https://www.gitbook.com/blog/what-is-okf-open-knowledge-format), a vendor-neutral markdown specification — and asked how the implementation measured up. The system had been asserting `okf_version: "0.1"` in `index.md` and citing "OKF v0.1 §9" in lint. Auditing the code against the spec rather than against our own documentation turned up two substantive gaps and two accepted trade-offs.

## Root causes worth remembering

1. **We compiled a knowledge graph and then threw the edges away.** `compile` built 9 nodes and 25 edges. `graph.json` was read for exactly one purpose: a ±4/±2 proximity nudge inside `_apply_graph_boost`. Prompt Cards contained **zero** links — verified across all nine — and the house schema *mandated* it ("plain text lines only, no link lists"). `index.md`, the spec's designated progressive-disclosure entry point, was never read by `pack` or `lookup` at all.

   What the agent actually received was top-k text fragments ranked by lexical similarity, with no relationships attached. That is structurally RAG with keyword matching substituted for embeddings — the exact approach OKF's comparison table places in the *other* column. We had built an anti-traversal layer on top of a traversal format and named it after the format.

   **The generalizable lesson:** compiling a graph is not the same as exposing one. If the consumer never sees an edge, the graph is a ranking feature, not a knowledge structure. Ask what the *agent* receives, not what the pipeline computes.

2. **Implementing four of five reserved fields felt like conformance.** The schema had `type`, `title`, `description`, and `tags`, and got the hard part right — `type` required, everything else optional, matching the spec's minimalism exactly. But `resource` was missing, and `scrape` had independently invented `source_url` for precisely the job `resource` exists to do, then buried the URL in body prose instead of queryable frontmatter. A bespoke field papered over the gap well enough that nobody noticed the reserved one was absent.

   **The lesson:** when you invent a field, check whether the spec already reserves one for that meaning. A local synonym is worse than the standard name, because it silently costs portability — the whole point of adopting a format.

3. **A conformance claim is a liability once written down.** `okf_version: "0.1"` had been sitting in `index.md` unaudited. Nothing verified it. Claims that no test or lint rule enforces will drift from reality and then get quoted back as fact.

## What changed

| Gap | Fix |
| --- | --- |
| Edges compiled but never exposed | `pack` appends `related:` per card — neighbours **not already in the pack**, capped at 3 (`related_links`, `0` disables) |
| Footers could displace cards | Attached *after* selection, so budget and card count are unaffected |
| `index.md` unused | Named as the browse entry point when a pack comes back empty |
| `resource` missing | First-class: parsed, indexed, emitted as a `source:` line, written by `scrape`; lint `DBG-310` / `DBG-311` |
| `source_url` | Removed — replaced by the reserved name |

Measured cost of traversal: ~8 tokens per link, +13–33% per pack depending on card count. Bought deliberately, after a session spent cutting tokens, because a flat ranked list is not a knowledge graph.

## Accepted trade-offs (decided, not overlooked)

1. **The agent keeps the name OKF.** It collides with a vendor-neutral spec authored by someone else, and the system is precisely the category of thing that spec says it is not ("not a runtime", "not a search index"). The user chose to keep it. Anyone reading `AGENTS.md` with spec knowledge will find this confusing — worth revisiting if the project is ever published.

2. **The runtime stays mandatory.** OKF's portability guarantee is that a bundle is plain markdown any agent reads with no SDK. `AGENTS.md` still declares `BLOCKED` for non-trivial work when Python is unavailable, which inverts that guarantee: the *data* is portable, the *workflow* is not. Defensible — the retrieval layer is real value the spec deliberately omits — but it means "OKF-conformant bundle" and "usable Brain" are not the same claim.

## Addendum — the spec had already moved to v0.2

Everything above was measured against v0.1, from secondary sources. Reading [`SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) directly showed the spec is at **v0.2**, and produced a worse finding than any of the above.

4. **We could not parse the format we are named after.** v0.2's whole contribution — provenance, trust, lifecycle, attestation — is expressed as nested YAML maps (`generated: {by, at}`, `sources: [{id, resource}]`, `executor: {resource, receipt}`). The hand-rolled subset parser rejects nested maps by design. Feeding it the spec's own worked example returned `None`: a conformant bundle from Google's reference agent would have been dropped document by document, which §4.1 forbids of a consumer.

   Skipping PyYAML was a defensible Laziness-Ladder call while frontmatter stayed flat. **The lesson is that a deliberate subset of a standard format is a bet on that format not growing.** v0.2 collected the bet. PyYAML is now used when importable, with the subset kept as a *declared-degraded* fallback that `capabilities` reports honestly — the difference between a limitation you announce and one you discover.

5. **The subset parser had been hiding invalid YAML.** The very first PyYAML run rejected `standards/ide-context-guardrails.md`: `pack_force_when: [@workspace, …]` is a parse error because `@` is a reserved YAML indicator. Our parser had accepted it for months. **A lenient parser does not make a corpus portable; it makes non-portability invisible.** We only found out by adopting a real one.

6. **Claiming a version is a liability unless something enforces it.** `okf_version: "0.1"` sat in `index.md` unaudited while the spec moved on, and lint cited "§9" for a section number that no longer meant what the comment implied. Meanwhile `log.md` violated §9's `MUST` on ISO date headings — a conformance criterion — and the change immediately before this one *added* a violating heading while announcing improved conformance.

7. **We built the trust problem and shipped none of the solution.** v0.2 exists because corpora are now written by agents. That is exactly this brain: agents deposit notes in `_inbox/`, a playbook promotes them, and they bind future agents as Prompt Cards that outrank the model's own judgement. We recorded no `generated.by`, no `verified`, no `sources` — an unreviewed machine guess and a human-verified standard were indistinguishable, and both bound equally. Cards now carry `trust: unverified` until a `human:` actor signs off, and all five binding standards currently show it. **The label is the point: it costs nothing when the news is good, so reviewing a document is what removes it.**

## Still open

**The vault only knows about itself.** All 9 concepts document OKF. The spec's worked example links an `orders` table to a weekly-active-users metric to a billing runbook — relationships between *domain* things. Traversal is now implemented, but there is nothing domain-shaped to traverse: 25 edges, every one self-referential. The graph machinery will not pay for itself until the vault holds knowledge this repository actually argues about.

**Nothing is verified.** Every concept is `generated: okf-agent/cursor` with no `verified` entry, which is honest but means the trust feature currently only ever reports bad news. The repo owner reviewing and signing the five binding standards with `verified: { by: human:<name>, at: … }` is what turns it into a working signal.

**`Attested Computation` is unimplemented.** Not applicable to engineering standards today, but the shape — a sanctioned procedure plus a deterministic attester that checks a receipt — is the natural home for "prove the lint/compile gate actually ran" if this brain ever gates CI.
