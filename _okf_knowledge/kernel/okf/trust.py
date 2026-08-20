"""
file_name: trust.py
description: OKF provenance, trust, and lifecycle helpers (SPEC §5, §7).
version: 1.0.0
authors: contributors

Knowledge in this brain is largely written by agents and then injected as
binding Prompt Cards that outrank the model's own judgement. The spec makes
"who wrote this, who checked it, is it still true" answerable from
frontmatter; this module is the single place those questions are answered.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from okf.paths import ACTOR_RE, ISO_DATE_RE, STATUS_VALUES

# §5.3 trust tiers, lowest to highest.
UNVERIFIED = "unverified"
MACHINE_CONFIRMED = "machine-confirmed"
HUMAN_REVIEWED = "human-reviewed"


def normalize_verified(fm: dict[str, object]) -> list[dict[str, object]]:
    """
    intent: Read `verified` as a list of events.
    input: frontmatter dict.
    output: list of {by, at} mappings (empty when absent/malformed).
    role: pure reader.
    side_effects: none.

    §5.2/§11: a consumer MUST treat a bare `verified: {by, at}` mapping as a
    one-element list, so producers may write either form.
    """
    raw = fm.get("verified")
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [e for e in raw if isinstance(e, dict)]
    return []


def trust_tier(fm: dict[str, object]) -> str:
    """
    intent: Derive the §5.3 trust tier from `verified`.
    input: frontmatter dict.
    output: unverified | machine-confirmed | human-reviewed.
    role: pure classifier.
    side_effects: none.

    The tier is derived, never stored: a stored verdict goes stale the moment
    someone re-verifies, and is not portable across consumers.
    """
    events = normalize_verified(fm)
    if not events:
        return UNVERIFIED
    for event in events:
        if str(event.get("by", "")).strip().startswith("human:"):
            return HUMAN_REVIEWED
    return MACHINE_CONFIRMED


def is_stale(fm: dict[str, object], today: date | None = None) -> bool:
    """
    intent: Apply §5.5 — a concept is stale when today >= stale_after.
    input: frontmatter dict; optional date for testing.
    output: bool (False when unset or unparseable).
    role: pure predicate.
    side_effects: none.
    """
    raw = str(fm.get("stale_after", "") or "").strip()
    if not ISO_DATE_RE.match(raw):
        return False
    try:
        deadline = date.fromisoformat(raw)
    except ValueError:
        return False
    return (today or datetime.now(timezone.utc).date()) >= deadline


def status_of(fm: dict[str, object]) -> str:
    """§5.4 — absent `status` means `stable`."""
    return str(fm.get("status", "") or "").strip() or "stable"


def _actor_findings(value: object, field: str) -> list[tuple[str, str, str]]:
    actor = str(value or "").strip()
    if not actor:
        return [("warning", "DBG-312", f"'{field}' is empty; §5.2 requires an actor")]
    if not ACTOR_RE.match(actor):
        return [
            (
                "warning",
                "DBG-313",
                f"'{field}' actor {actor!r} does not follow §7 "
                "(human:<name> | process:<name> | <agent>/<model>)",
            )
        ]
    return []


def check_trust(fm: dict[str, object]) -> list[tuple[str, str, str]]:
    """
    intent: Validate the OKF provenance/trust/lifecycle families.
    input: frontmatter dict.
    output: list of (severity, code, message) — empty when clean.
    role: pure checker, consumed by lint.
    side_effects: none.

    Every family is optional (§5): absence is meaningful, never an error. These
    findings fire only when a producer opted in and then got the shape wrong.
    """
    out: list[tuple[str, str, str]] = []

    generated = fm.get("generated")
    if generated is not None:
        if not isinstance(generated, dict):
            out.append(("warning", "DBG-312", "'generated' must be a { by, at } mapping"))
        else:
            out.extend(_actor_findings(generated.get("by"), "generated.by"))

    for event in normalize_verified(fm):
        out.extend(_actor_findings(event.get("by"), "verified[].by"))
    if "verified" in fm and not normalize_verified(fm):
        out.append(("warning", "DBG-312", "'verified' must be a { by, at } mapping or a list of them"))

    status = str(fm.get("status", "") or "").strip()
    if status and status not in STATUS_VALUES:
        out.append(
            (
                "warning",
                "DBG-314",
                f"status {status!r} is not one of {' | '.join(STATUS_VALUES)} (§5.4)",
            )
        )

    stale_after = str(fm.get("stale_after", "") or "").strip()
    if stale_after:
        if not ISO_DATE_RE.match(stale_after):
            out.append(("warning", "DBG-315", f"stale_after {stale_after!r} must be YYYY-MM-DD (§5.5)"))
        elif is_stale(fm):
            out.append(("warning", "DBG-315", f"content is past stale_after {stale_after}"))

    sources = fm.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            out.append(("warning", "DBG-316", "'sources' must be a list of entries (§5.1)"))
        else:
            for idx, entry in enumerate(sources):
                if not isinstance(entry, dict):
                    out.append(("warning", "DBG-316", f"sources[{idx}] must be a mapping"))
                elif not str(entry.get("resource", "") or "").strip():
                    out.append(
                        ("warning", "DBG-316", f"sources[{idx}] is missing required 'resource' (§5.1)")
                    )
    return out
