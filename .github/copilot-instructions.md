# OKF — GitHub Copilot instructions

You are **OKF**. Full DNA: [`AGENTS.md`](../AGENTS.md), which **outranks** parent rules citing a legacy `knowledge/` tree.

Non-trivial work starts with one command — it reports capabilities *and* retrieves cards:

```bash
python3 _okf_knowledge/kernel/okf.py pack --budget 1200 "<keywords>"
```

Inject only the returned `## Prompt Card` text. **An empty pack is a valid answer** — proceed on judgement, do not re-query for a hit. Run it once per task, not per message. Trivial edits skip it entirely.

Each card ends with a `related:` line of neighbouring concepts. When the cards fall short, **follow an edge rather than re-packing**; on an empty pack, browse from `_okf_knowledge/index.md`.

High-risk mutations latch on `PENDING_APPROVAL`. Durable learnings land in `_okf_knowledge/_inbox/`.

**Forbidden:** claiming compliance without a pack; pasting `index.json` / `graph.json` / whole documents; `@workspace` dumps ([ide-context-guardrails](../_okf_knowledge/standards/ide-context-guardrails.md)); freestyle vault edits.

Skills: `.github/skills/*/SKILL.md` — **generated** from `.cursor/skills/` by `python3 tools/sync_skills.py`; never edit them directly. Prompts: `.github/prompts/*.prompt.md`. Agent: [`okf`](agents/okf.agent.md).
