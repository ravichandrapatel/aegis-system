#!/usr/bin/env python3
# file_name: test_okf_smoke.py
# description: Stdlib smoke tests for OKF kernel harden paths.
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
KERNEL = ROOT / "_okf_knowledge" / "kernel"
sys.path.insert(0, str(KERNEL))


class OkfSmokeTests(unittest.TestCase):
    def test_imports(self) -> None:
        from src import (  # noqa: F401
            cards,
            cli,
            compile_cmd,
            enrich_cmd,
            lint_cmd,
            lookup,
            optimize_cmd,
            pack_cmd,
            scrape_cmd,
            serve_cmd,
            vault,
        )

        self.assertTrue(callable(enrich_cmd._llm_chat))
        self.assertTrue(callable(enrich_cmd._apply_enrich))
        self.assertTrue(hasattr(optimize_cmd, "datetime"))
        self.assertTrue(callable(pack_cmd.assemble_prompt_pack))
        self.assertTrue(callable(lookup.lookup))
        self.assertTrue(callable(lookup.load_index))
        self.assertTrue(callable(compile_cmd._atomic_write_text))

    def test_frontmatter_block_list(self) -> None:
        from src.vault import parse_frontmatter

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
        from src.lint_cmd import cmd_lint
        from src.lookup import lookup
        from src.pack_cmd import assemble_prompt_pack

        hits = lookup("guardrails", limit=3)
        self.assertTrue(hits, "expected at least one hit for 'guardrails'")
        pack, pack_hits = assemble_prompt_pack("guardrails", limit=2)
        self.assertTrue(pack_hits)
        self.assertTrue(pack)
        self.assertEqual(cmd_lint(None), 0)

    def test_enrich_escape_description(self) -> None:
        from src.enrich_cmd import _apply_enrich
        from src.models import Concept

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                "---\ntype: Concept\ntitle: Sample\ndescription: old\n"
                "tags: [a]\ntimestamp: 2026-01-01T00:00:00Z\n---\n\n## Body\n",
                encoding="utf-8",
            )
            concept = Concept(
                concept_id="sample",
                path=path,
                frontmatter={
                    "type": "Concept",
                    "title": "Sample",
                    "description": "old",
                    "tags": ["a"],
                },
                body="\n## Body\n",
            )
            text, filled = _apply_enrich(
                concept,
                ["description"],
                {"description": "has: colon and 'quotes'"},
            )
            self.assertIn("description", filled)
            self.assertIn('description: "has: colon and \'quotes\'"', text)

    def test_serve_loopback_gate(self) -> None:
        from src.serve_cmd import _is_loopback

        self.assertTrue(_is_loopback("127.0.0.1"))
        self.assertTrue(_is_loopback("::1"))
        self.assertFalse(_is_loopback("0.0.0.0"))
        self.assertFalse(_is_loopback("192.168.1.1"))

    def test_xml_cdata_no_breakout(self) -> None:
        from src.pack_cmd import format_pack
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
        from src.scrape_cmd import _validate_fetch_url

        with self.assertRaises(SystemExit):
            _validate_fetch_url("http://127.0.0.1/secret")
        with self.assertRaises(SystemExit):
            _validate_fetch_url("http://10.0.0.1/")
        with self.assertRaises(SystemExit):
            _validate_fetch_url("file:///etc/passwd")

    def test_enrich_ssrf_blocks_private_cloud(self) -> None:
        from src.enrich_cmd import _validate_llm_endpoint, _validate_llm_redirect

        with self.assertRaises(ValueError):
            _validate_llm_endpoint("http://10.0.0.5/v1/chat/completions")
        # Configured local models intentionally allowed.
        _validate_llm_endpoint("http://127.0.0.1:11434/v1/chat/completions")
        # Redirects must NOT inherit the local allow-list (scrape parity).
        with self.assertRaises(ValueError):
            _validate_llm_redirect("http://127.0.0.1/secret")
        with self.assertRaises(ValueError):
            _validate_llm_redirect("http://evil.local/v1/chat/completions")
        with self.assertRaises(ValueError):
            _validate_llm_endpoint(
                "http://127.0.0.1/secret", allow_local=False
            )

    def test_atomic_write_text(self) -> None:
        from src.compile_cmd import _atomic_write_text

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            _atomic_write_text(path, '{"ok": true}\n')
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})
            leftovers = list(Path(tmp).glob(".out.json.*.tmp"))
            self.assertEqual(leftovers, [])

    def test_scrape_path_traversal_blocked(self) -> None:
        from src.scrape_cmd import _safe_ref_segment, write_reference

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

    def test_enrich_block_list_and_body_description(self) -> None:
        from src.enrich_cmd import _apply_enrich
        from src.models import Concept
        from src.vault import parse_frontmatter

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "block.md"
            path.write_text(
                "---\ntype: Concept\ntitle: Sample\n"
                "tags:\n  - a\n"
                "timestamp: 2026-01-01T00:00:00Z\n---\n\n"
                "description: body-line\n\n## Body\n",
                encoding="utf-8",
            )
            concept = Concept(
                concept_id="block",
                path=path,
                frontmatter={
                    "type": "Concept",
                    "title": "Sample",
                    "tags": ["a"],
                    "timestamp": "2026-01-01T00:00:00Z",
                },
                body="\ndescription: body-line\n\n## Body\n",
            )
            text, filled = _apply_enrich(
                concept,
                ["description", "tags"],
                {"description": "NEWSAFE", "tags": ["b"]},
            )
            self.assertEqual(set(filled), {"description", "tags"})
            fm, body = parse_frontmatter(text)
            self.assertIsNotNone(fm)
            assert fm is not None
            self.assertEqual(fm.get("description"), "NEWSAFE")
            self.assertEqual(fm.get("tags"), ["a", "b"])
            # Must not leave orphan block-list dashes after tags.
            head = text.split("---", 2)[1]
            self.assertNotRegex(head, r"(?m)^\s+-\s+")
            # Body description line must remain untouched.
            self.assertIn("description: body-line", body)

    def test_compile_cache_requires_hash(self) -> None:
        from src.compile_cmd import _sha256_bytes, load_vault_incremental
        from src.paths import COMPILE_CACHE_VERSION, VAULT_ROOT
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

    def test_serve_csrf_origin_gate(self) -> None:
        from src.serve_cmd import _origin_is_loopback

        self.assertTrue(_origin_is_loopback(""))
        self.assertTrue(_origin_is_loopback("http://127.0.0.1:8765/"))
        self.assertTrue(_origin_is_loopback("http://localhost:8765/aegis-brain.html"))
        self.assertFalse(_origin_is_loopback("https://evil.example/"))
        self.assertFalse(_origin_is_loopback("http://192.168.1.10/"))

    def test_enrich_redirect_handler_blocks_loopback(self) -> None:
        from src.enrich_cmd import _SafeLlmRedirectHandler
        import urllib.request

        handler = _SafeLlmRedirectHandler()
        req = urllib.request.Request(
            "https://example.com/v1/chat/completions",
            data=b"{}",
            headers={"Authorization": "Bearer secret-token", "Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(ValueError):
            handler.redirect_request(
                req, None, 302, "Found", {}, "http://127.0.0.1:11434/v1/chat/completions"
            )
        with self.assertRaises(ValueError):
            handler.redirect_request(
                req, None, 302, "Found", {}, "http://metadata.local/latest"
            )

    def test_argparse_imported_on_cmd_modules(self) -> None:
        from src import cards, lint_cmd, optimize_cmd

        for mod in (cards, lint_cmd, optimize_cmd):
            self.assertTrue(hasattr(mod, "argparse"), f"{mod.__name__} missing argparse import")
            self.assertTrue(hasattr(mod.argparse, "Namespace"))

    def test_serve_does_not_expose_vault_paths(self) -> None:
        from src.serve_cmd import VaultHandler, _is_loopback
        from http.server import HTTPServer

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
            conn.request("GET", "/aegis-brain.html")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            resp.read()
            conn.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
