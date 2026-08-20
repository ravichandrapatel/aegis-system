#!/usr/bin/env python3
# file_name: test_okf_smoke.py
# description: Stdlib smoke tests for OKF runtime harden paths.
# version: 0.2.0
# authors: contributors
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "_okf_knowledge"
TOOLING = BRAIN / "kernel"
sys.path.insert(0, str(TOOLING))


class OkfSmokeTests(unittest.TestCase):
    def test_imports(self) -> None:
        from okf import (  # noqa: F401
            cards,
            cli,
            compile,
            lint,
            lookup,
            optimize,
            pack,
            scrape,
            serve,
            tokens,
            vault,
        )

        self.assertTrue(hasattr(optimize, "datetime"))
        self.assertTrue(callable(pack.assemble_prompt_pack))
        self.assertTrue(callable(lookup.lookup))
        self.assertTrue(callable(lookup.load_index))
        self.assertTrue(callable(compile._atomic_write_text))
        self.assertTrue(callable(tokens.count_paths))

    def test_package_naming_is_clean(self) -> None:
        from okf.style import check_package_naming

        findings = check_package_naming()
        self.assertEqual(
            findings,
            [],
            msg="runtime package must satisfy standards/python-naming.md:\n"
            + "\n".join(
                f"{f['concept']}: [{f['code']}] {f['message']}" for f in findings
            ),
        )

    def test_naming_rejects_banned_prefix_and_camel(self) -> None:
        import ast
        from pathlib import Path

        from okf.style import _scan_tree

        src = "okf_config = 1\nmaxCards = 2\ndef BadName():\n    pass\n"
        tree = ast.parse(src)
        findings = _scan_tree(tree, Path("okf/_fixture.py"))
        codes = {f["code"] for f in findings}
        self.assertIn("DBG-321", codes)
        self.assertIn("DBG-320", codes)

    def test_tokens_count_file_and_dir(self) -> None:
        from okf.tokens import count_paths, token_method

        agents = ROOT / "AGENTS.md"
        report = count_paths([str(agents)])
        self.assertEqual(report["file_count"], 1)
        self.assertGreater(int(report["total_tokens"]), 0)
        self.assertIn(token_method(), ("heuristic", "tiktoken:cl100k_base"))

        std = ROOT / "_okf_knowledge" / "standards"
        dir_report = count_paths([str(std)], extensions=["md"])
        self.assertGreaterEqual(int(dir_report["file_count"]), 1)
        self.assertGreater(int(dir_report["total_tokens"]), 0)

    def test_frontmatter_block_list(self) -> None:
        from okf.vault import parse_frontmatter

        text = (
            "---\ntype: Concept\ntags:\n  - standard\n  - okf\n"
            "title: T\ndescription: D\n---\n\nBody\n"
        )
        fm, body = parse_frontmatter(text)
        self.assertIsNotNone(fm)
        assert fm is not None
        self.assertEqual(fm.get("tags"), ["standard", "okf"])
        self.assertIn("Body", body)

    def test_lookup_and_lint(self) -> None:
        from okf.lint import cmd_lint
        from okf.lookup import lookup
        from okf.pack import assemble_prompt_pack

        hits = lookup("guardrails", limit=3)
        self.assertTrue(hits, "expected at least one hit for 'guardrails'")
        pack, pack_hits = assemble_prompt_pack("guardrails", limit=2)
        self.assertTrue(pack_hits)
        self.assertTrue(pack)
        self.assertEqual(cmd_lint(None), 0)

    def test_serve_loopback_gate(self) -> None:
        from okf.serve import _is_loopback

        self.assertTrue(_is_loopback("127.0.0.1"))
        self.assertTrue(_is_loopback("::1"))
        self.assertFalse(_is_loopback("0.0.0.0"))
        self.assertFalse(_is_loopback("192.168.1.1"))

    def test_xml_cdata_no_breakout(self) -> None:
        from okf.pack import format_pack
        import xml.etree.ElementTree as ET

        evil = [
            {
                "id": "x",
                "path": "x.md",
                "type": "Concept",
                "title": "t",
                "score": 1,
                "kind": "card",
                "tokens": 1,
                "text": "before ]]> <boom/> after",
            }
        ]
        xml = format_pack(evil, "xml", "q")
        # Must parse as well-formed XML; text round-trips with terminator intact.
        root = ET.fromstring(xml)
        card = root.find("card")
        self.assertIsNotNone(card)
        assert card is not None
        self.assertEqual((card.text or "").strip(), "before ]]> <boom/> after")

    def test_scrape_ssrf_blocks_private(self) -> None:
        from okf.scrape import _validate_fetch_url

        with self.assertRaises(SystemExit):
            _validate_fetch_url("http://127.0.0.1/secret")
        with self.assertRaises(SystemExit):
            _validate_fetch_url("http://10.0.0.1/")
        with self.assertRaises(SystemExit):
            _validate_fetch_url("file:///etc/passwd")

    def test_atomic_write_text(self) -> None:
        from okf.compile import _atomic_write_text

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            _atomic_write_text(path, '{"ok": true}\n')
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})
            leftovers = list(Path(tmp).glob(".out.json.*.tmp"))
            self.assertEqual(leftovers, [])

    def test_scrape_path_traversal_blocked(self) -> None:
        from okf.scrape import _safe_ref_segment, write_reference

        with self.assertRaises(ValueError):
            _safe_ref_segment("../../../outside", label="domain")
        with self.assertRaises(ValueError):
            _safe_ref_segment("a/b", label="slug")
        with self.assertRaises(ValueError):
            write_reference(
                slug="pwn",
                title="Pwn",
                url="https://example.com/docs",
                content="safe body text for reference",
                domain="../../../outside",
            )

    def test_compile_cache_requires_hash(self) -> None:
        from okf.compile import _sha256_bytes, load_vault_incremental
        from okf.paths import COMPILE_CACHE_VERSION, VAULT_ROOT
        import os

        a = _sha256_bytes(b"content-a")
        b = _sha256_bytes(b"content-b")
        self.assertNotEqual(a, b)
        self.assertEqual(_sha256_bytes(b"same"), _sha256_bytes(b"same"))

        # Poison cache: matching mtime + wrong sha256 must NOT reuse.
        cache = VAULT_ROOT / ".okf-compile-cache.json"
        concepts = list((VAULT_ROOT / "standards").glob("*.md"))
        self.assertTrue(concepts)
        sample = concepts[0]
        rel = str(sample.relative_to(VAULT_ROOT)).replace("\\", "/")
        mtime_ns = sample.stat().st_mtime_ns
        poison = {
            "version": COMPILE_CACHE_VERSION,
            "files": {
                rel: {
                    "mtime_ns": mtime_ns,
                    "sha256": "0" * 64,
                    "concept": {
                        "concept_id": "poisoned",
                        "frontmatter": {"type": "Concept", "title": "Poison"},
                        "body": "",
                        "parse_error": None,
                    },
                }
            },
        }
        prev = cache.read_text(encoding="utf-8") if cache.is_file() else None
        try:
            cache.write_text(json.dumps(poison) + "\n", encoding="utf-8")
            os.utime(sample, ns=(sample.stat().st_atime_ns, mtime_ns))
            loaded, dirty, reused = load_vault_incremental(force=False)
            ids = {c.concept_id for c in loaded}
            self.assertNotIn("poisoned", ids)
            # At least the mismatched file was re-parsed (dirty), not reused from poison.
            self.assertGreaterEqual(dirty, 1)
        finally:
            if prev is None:
                if cache.is_file():
                    cache.unlink()
            else:
                cache.write_text(prev, encoding="utf-8")

    def test_argparse_imported_on_command_modules(self) -> None:
        from okf import cards, lint, optimize

        for mod in (cards, lint, optimize):
            self.assertTrue(hasattr(mod, "argparse"), f"{mod.__name__} missing argparse import")
            self.assertTrue(hasattr(mod.argparse, "Namespace"))

    def test_serve_is_read_only_and_hides_vault_paths(self) -> None:
        """serve exposes no mutate endpoints, so nothing needs authentication."""
        from okf.serve import VaultHandler, _is_loopback
        from http.server import HTTPServer

        self.assertFalse(
            hasattr(VaultHandler, "do_POST"),
            "serve must stay read-only — a mutate endpoint would need auth again",
        )
        for verb in ("do_PUT", "do_DELETE", "do_PATCH"):
            self.assertFalse(hasattr(VaultHandler, verb), f"unexpected {verb} on serve")

        self.assertTrue(_is_loopback("127.0.0.1"))
        server = HTTPServer(("127.0.0.1", 0), VaultHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/standards/index.md")
            resp = conn.getresponse()
            body = resp.read()
            self.assertEqual(resp.status, 404)
            self.assertIn(b"not served", body.lower())
            conn.close()

            conn = HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/okf-brain.html")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            resp.read()
            conn.close()

            # POST must not be handled at all now.
            conn = HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("POST", "/api/compile")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 501)
            resp.read()
            conn.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
