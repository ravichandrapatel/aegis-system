#!/usr/bin/env python3
# file_name: test_retrieval_quality.py
# description: Relevance tests for OKF lookup/pack — precision, recall, budget, force-include.
# version: 1.0.0
# authors: contributors
"""
intent: Guard retrieval QUALITY, not just "did it return something".
role: regression suite for the scoring and pack-assembly rules.

The smoke suite only asserted that hits were non-empty, which let two real
defects ship: pack_force_when matched bare substrings ("tab" fired on "table"),
and description-only tokens were scored as exact title hits.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "_okf_knowledge"
TOOLING = BRAIN / "kernel"
sys.path.insert(0, str(TOOLING))


class PackForceWhenTests(unittest.TestCase):
    """pack_force_when must match on token boundaries, never bare substrings."""

    def _match(self, query: str, keywords: list[str]) -> bool:
        from okf.pack import _query_matches_pack_force

        return _query_matches_pack_force(query, keywords)

    def test_whole_word_matches(self) -> None:
        self.assertTrue(self._match("close the extra tab", ["tab"]))
        self.assertTrue(self._match("deploy to staging", ["deploy"]))
        self.assertTrue(self._match("count the token budget", ["token"]))

    def test_substring_does_not_match(self) -> None:
        cases = [
            ("database table schema", ["tab"]),
            ("stable release notes", ["tab"]),
            ("a portable package", ["tab"]),
            ("terraform kubernetes deployment", ["deploy"]),
            ("redeploy the service", ["deploy"]),
            ("swap the tokenizer", ["token"]),
            ("extended warranty", ["extend"]),
        ]
        for query, keywords in cases:
            with self.subTest(query=query):
                self.assertFalse(
                    self._match(query, keywords),
                    f"{keywords} must not fire on {query!r}",
                )

    def test_multiword_keyword_requires_contiguous_phrase(self) -> None:
        self.assertTrue(self._match("inject a prompt card please", ["prompt card"]))
        self.assertFalse(self._match("prompt the user, then card him", ["prompt card"]))

    def test_empty_inputs_are_safe(self) -> None:
        self.assertFalse(self._match("", ["tab"]))
        self.assertFalse(self._match("anything", []))
        self.assertFalse(self._match("anything", [""]))


class RelevanceFloorTests(unittest.TestCase):
    """Off-topic queries must return an empty pack, not a confident wrong card."""

    def _pack(self, query: str):
        from okf.pack import assemble_prompt_pack

        return assemble_prompt_pack(query, limit=5)

    def test_offtopic_queries_return_nothing(self) -> None:
        for query in (
            "how do I bake a cake",
            "terraform kubernetes helm deployment",
            "redeploy the tokenizer",
            "stable release notes",
        ):
            with self.subTest(query=query):
                pack, _ = self._pack(query)
                self.assertEqual(
                    pack, [], f"{query!r} should yield no cards, got {[r['id'] for r in pack]}"
                )

    def test_floor_can_be_disabled(self) -> None:
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("how do I bake a cake", limit=5, min_score=0)
        self.assertTrue(pack, "min_score=0 should restore unfiltered behaviour")


class RankingTests(unittest.TestCase):
    """Known queries must surface the specific concept a human would expect."""

    EXPECTED = [
        ("prompt injection rule", "standards/okf-prompt-injection"),
        ("capability discovery", "vault/concepts/okf-capability-discovery"),
        ("ide context guardrails workspace", "standards/ide-context-guardrails"),
        ("extending okf replicate", "vault/concepts/extending-okf"),
        ("maintain okf system playbook", "vault/playbooks/maintain-okf-system"),
        ("house schema frontmatter", "standards/okf-house-schema"),
        ("simplicity laziness ladder", "standards/simplicity-first"),
        ("metadata headers", "standards/metadata-headers"),
        ("cognitive bundle", "vault/concepts/okf-cognitive-bundle"),
    ]

    def test_top_hit_is_the_expected_concept(self) -> None:
        from okf.pack import assemble_prompt_pack

        for query, expected_id in self.EXPECTED:
            with self.subTest(query=query):
                pack, _ = assemble_prompt_pack(query, limit=5)
                self.assertTrue(pack, f"{query!r} returned no cards")
                self.assertEqual(
                    pack[0]["id"],
                    expected_id,
                    f"{query!r} ranked {pack[0]['id']} above {expected_id}",
                )

    def test_description_token_does_not_outrank_title(self) -> None:
        """A word present only in a description must not score as a title hit."""
        from okf.lookup import lookup

        hits = lookup("how", limit=5)
        for hit in hits:
            with self.subTest(concept=hit.entry.concept_id):
                self.assertLess(
                    hit.score,
                    24,
                    f"{hit.entry.concept_id} scored {hit.score} for a stopword-ish term",
                )


class BudgetTests(unittest.TestCase):
    """The pack must never exceed its token budget."""

    def test_budget_is_respected(self) -> None:
        from okf.config import count_tokens
        from okf.pack import assemble_prompt_pack

        for budget in (20, 60, 200, 1200):
            with self.subTest(budget=budget):
                pack, _ = assemble_prompt_pack("prompt card injection", limit=8, budget=budget)
                total = sum(count_tokens(str(row["text"])) for row in pack)
                self.assertLessEqual(
                    total, budget, f"pack used {total} tokens against a {budget} budget"
                )

    def test_max_cards_is_respected(self) -> None:
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("okf", limit=20, max_cards=2, budget=100_000)
        self.assertLessEqual(len(pack), 2)


def _footer_lines(row: dict, prefix: str) -> list[str]:
    """
    Footer lines only. A card body may legitimately talk *about* `related:`
    (the retrieval standard does), so substring matching gives false positives.
    """
    return [
        line[len(prefix):].strip()
        for line in str(row["text"]).splitlines()
        if line.startswith(prefix)
    ]


class TraversalTests(unittest.TestCase):
    """
    Cards must carry their graph edges. Without this the pack is a flat ranked
    blob and the agent can only re-query, which is the RAG behaviour OKF exists
    to replace.
    """

    def test_cards_expose_related_edges(self) -> None:
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("prompt card schema frontmatter", limit=5)
        self.assertTrue(pack)
        self.assertTrue(
            any(_footer_lines(row, "related:") for row in pack),
            "no card exposed its graph neighbours",
        )

    def test_related_omits_concepts_already_in_pack(self) -> None:
        """Pointing at a card the agent already holds costs tokens and adds no reach."""
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("okf", limit=20, max_cards=8, budget=100_000)
        in_pack = {str(row["id"]) for row in pack}
        for row in pack:
            for line in _footer_lines(row, "related:"):
                for part in line.split("·"):
                    cid = part.split(" (+")[0].strip().removesuffix(".md")
                    if not cid:
                        continue
                    with self.subTest(card=row["id"], neighbour=cid):
                        self.assertNotIn(cid, in_pack)

    def test_related_links_can_be_disabled(self) -> None:
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("prompt card schema", limit=5, related_links=0)
        for row in pack:
            self.assertFalse(_footer_lines(row, "related:"))

    def test_traversal_never_breaks_the_budget(self) -> None:
        """Footers are attached after selection, so they must yield to the ceiling."""
        from okf.config import count_tokens
        from okf.pack import assemble_prompt_pack

        for budget in (20, 60, 200, 1200):
            with self.subTest(budget=budget):
                pack, _ = assemble_prompt_pack("okf prompt card", limit=8, budget=budget)
                total = sum(count_tokens(str(row["text"])) for row in pack)
                self.assertLessEqual(total, budget)

    def test_empty_pack_names_the_entry_point(self) -> None:
        from okf.pack import format_pack

        out = format_pack([], "markdown", "quantum photonics fabrication")
        self.assertIn("index.md", out)


class ResourceFieldTests(unittest.TestCase):
    """`resource` is an OKF reserved field and must survive compile→lookup."""

    def test_resource_round_trips_through_the_index(self) -> None:
        from okf.compile import _index_row_for_concept
        from okf.lookup import _entry_from_row
        from okf.models import Concept

        url = "https://example.invalid/docs/thing"
        row = _index_row_for_concept(
            Concept(
                concept_id="vault/references/example/thing",
                path=Path("thing.md"),
                frontmatter={"type": "Reference", "title": "Thing", "resource": url},
            )
        )
        self.assertEqual(row["resource"], url)
        self.assertEqual(_entry_from_row(row).resource, url)

    def test_resource_is_surfaced_as_a_source_line(self) -> None:
        from okf.models import Hit, IndexEntry
        from okf.pack import _traversal_footer

        hit = Hit(
            entry=IndexEntry(concept_id="vault/references/x/y", resource="https://e.invalid/d"),
            score=100,
        )
        self.assertIn("source: https://e.invalid/d", _traversal_footer(hit, {}, set(), 3))


V02_DOC = """---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year.
tags: [finance, revenue]
status: stable
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-20T22:53:05Z }
verified: { by: human:ahormati, at: 2026-06-25T09:00:00Z }
stale_after: 2026-09-23
sources:
  - id: rev-policy
    resource: https://wiki.acme/finance/revenue-recognition
    title: Revenue recognition policy
---

# Computation
"""


class SpecV02ParsingTests(unittest.TestCase):
    """
    A consumer that rejects a conformant bundle is broken (SPEC §4.1). The
    hand-rolled subset parser did exactly that for every trust field.
    """

    def test_v02_frontmatter_parses(self) -> None:
        import json

        from okf.vault import parse_frontmatter, yaml_available

        if not yaml_available():
            self.skipTest("PyYAML absent — subset fallback cannot represent nested maps")
        fm, body = parse_frontmatter(V02_DOC)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["type"], "Attested Computation")
        self.assertEqual(fm["generated"]["by"], "reference_agent/gemini-2.5-pro")
        self.assertEqual(fm["sources"][0]["id"], "rev-policy")
        self.assertEqual(fm["executor"]["receipt"], ["job_id", "executed_sql", "result"])
        self.assertIn("# Computation", body)
        # Dates must survive as strings or compile/index writing raises.
        json.dumps(fm)

    def test_yaml_reserved_indicator_is_rejected(self) -> None:
        """`@` unquoted is invalid YAML; the old parser silently accepted it."""
        from okf.vault import parse_frontmatter, yaml_available

        if not yaml_available():
            self.skipTest("PyYAML absent")
        fm, _ = parse_frontmatter("---\npack_force_when: [@workspace]\n---\nbody\n")
        self.assertIsNone(fm)

    def test_subset_fallback_rejects_rather_than_mangles(self) -> None:
        from okf.vault import _parse_frontmatter_subset

        fm, _ = _parse_frontmatter_subset(V02_DOC)
        self.assertIsNone(fm)


class TrustTests(unittest.TestCase):
    """SPEC §5 — derived trust, never stored."""

    def test_tiers(self) -> None:
        from okf.trust import HUMAN_REVIEWED, MACHINE_CONFIRMED, UNVERIFIED, trust_tier

        self.assertEqual(trust_tier({}), UNVERIFIED)
        self.assertEqual(
            trust_tier({"verified": {"by": "process:nightly", "at": "x"}}), MACHINE_CONFIRMED
        )
        self.assertEqual(
            trust_tier({"verified": [{"by": "human:ghost", "at": "x"}]}), HUMAN_REVIEWED
        )

    def test_bare_verified_mapping_is_a_one_element_list(self) -> None:
        """§5.2/§11: consumers MUST accept the un-listed form."""
        from okf.trust import normalize_verified

        self.assertEqual(len(normalize_verified({"verified": {"by": "human:a", "at": "x"}})), 1)

    def test_staleness_is_an_absolute_date_comparison(self) -> None:
        from datetime import date

        from okf.trust import is_stale

        self.assertTrue(is_stale({"stale_after": "2026-01-01"}, today=date(2026, 1, 1)))
        self.assertFalse(is_stale({"stale_after": "2026-01-02"}, today=date(2026, 1, 1)))
        self.assertFalse(is_stale({}, today=date(2026, 1, 1)))

    def test_lint_catches_malformed_families(self) -> None:
        from okf.trust import check_trust

        codes = {c for _, c, _ in check_trust({"status": "active"})}
        self.assertIn("DBG-314", codes)
        codes = {c for _, c, _ in check_trust({"generated": {"by": "cursor"}})}
        self.assertIn("DBG-313", codes)
        codes = {c for _, c, _ in check_trust({"sources": [{"title": "no resource"}]})}
        self.assertIn("DBG-316", codes)

    def test_clean_v02_frontmatter_has_no_findings(self) -> None:
        from okf.trust import check_trust
        from okf.vault import parse_frontmatter, yaml_available

        if not yaml_available():
            self.skipTest("PyYAML absent")
        fm, _ = parse_frontmatter(V02_DOC)
        # stale_after is in the past, so only the staleness notice is expected.
        codes = {c for _, c, _ in check_trust(fm)}
        self.assertLessEqual(codes, {"DBG-315"})

    def test_unverified_cards_stay_silent(self) -> None:
        """Default unverified must not tax every pack with a trust: line."""
        from okf.pack import assemble_prompt_pack

        pack, _ = assemble_prompt_pack("prompt card schema frontmatter", limit=5)
        self.assertTrue(pack)
        for row in pack:
            self.assertFalse(
                _footer_lines(row, "trust:"),
                f"{row.get('id')} unexpectedly labelled trust while unverified",
            )

    def test_machine_confirmed_is_labelled(self) -> None:
        from okf.models import Hit, IndexEntry
        from okf.pack import _traversal_footer
        from okf.trust import MACHINE_CONFIRMED

        hit = Hit(
            entry=IndexEntry(
                concept_id="vault/concepts/x",
                trust=MACHINE_CONFIRMED,
            ),
            score=100,
        )
        footer = _traversal_footer(hit, {}, set(), 0)
        self.assertIn(f"trust: {MACHINE_CONFIRMED}", footer)


class CapabilityLineTests(unittest.TestCase):
    """pack folds discovery in, so the line must be present and single-line."""

    def test_compact_line_shape(self) -> None:
        from okf.capabilities import compact_capability_line

        line = compact_capability_line()
        self.assertNotIn("\n", line)
        self.assertTrue(line.startswith("caps: "))
        self.assertIn("features:", line)


if __name__ == "__main__":
    unittest.main()
