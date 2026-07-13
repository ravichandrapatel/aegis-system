# 7. Profiles

[← Table of contents](README.md)

Profiles live under `_okf_knowledge/kernel/profiles/` and have frontmatter `type: Profile`.

They define **operational context**: which modules, vendors, standards, and roles are in play for a request.

## Why profiles exist

Without a profile, an agent may load irrelevant vendors, miss required capabilities, or apply the wrong evidence bar.

With a profile:

```
Intent → Load Profile → Capability Check → (only then) Graph traversal / generation
```

If something the profile requires is missing → **HALT** exit code **4** (Unsupported).

## Typical profile names

| Profile (example) | Intended use |
| --- | --- |
| `operator.md` | Day-2 operate / troubleshoot / deploy loops |
| `architect.md` | Design, compare, generation planning |
| `migration.md` | Migrate / upgrade programs with stricter gates |

Starter stubs may exist as placeholders — flesh them out with explicit allow-lists before relying on them in production.

## What a Profile should declare

Recommended content (adapt to your schema file under `profiles/`):

| Section | Purpose |
| --- | --- |
| **Role / persona** | Who is acting (operator, architect, …) |
| **Allowed modules** | Paths or ids under `kernel/modules/` |
| **Allowed vendors** | Paths or ids under `kernel/vendors/` |
| **Required standards** | Must be present and active |
| **Evidence policy** | Which grades are allowed (`assumed` banned in prod) |
| **Default intents** | Intents this profile typically serves |

Follow the house frontmatter schema ([Frontmatter](05-frontmatter-schema.md)) plus any fields documented in `kernel/profiles/_schema.md` as you expand it.

## When to use which profile

| Situation | Prefer |
| --- | --- |
| User asks to **design / CREATE** architecture | `architect` |
| User asks to **DEPLOY / UPGRADE / ROLLBACK** | `operator` (or a dedicated deploy profile) |
| Large **MIGRATE** program | `migration` |
| **MAINTAIN / INGEST** brain edits | Still use maintain playbook; profile may be `architect` or a maintainer profile if you define one |
| **REVIEW** a PR against house law | `architect` or `operator` depending on runtime vs design focus |

If no profile matches, **do not invent capabilities**. Either select the closest explicit profile or halt with missing-input / unsupported semantics.

## Capability check checklist

Before Path A/B/C work:

- [ ] Profile file exists and parses  
- [ ] Every listed module path exists  
- [ ] Every listed vendor path exists  
- [ ] Every required standard exists and is `active`  
- [ ] Evidence policy forbids `assumed` when operating production  

Failure → report missing dependencies; exit **4**.

## Profiles vs Modules vs Vendors

| Artifact | Answers |
| --- | --- |
| **Profile** | *Which* capabilities may load for this job? |
| **Module** | *How* does our core domain execute / own artifacts? |
| **Vendor** | *How* does a specific cloud/tool extend execution? |

## Related

- [Protocol & routing](06-protocol-routing.md) § Capability Check  
- [Document types](04-document-types.md)  
- [`AGENTS.md` §4.1](../AGENTS.md)
