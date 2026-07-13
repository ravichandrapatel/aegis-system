#!/usr/bin/env python3
# file_name: serve_vault.py
# description: Static file server for the Aegis OKF vault with a POST /api/lint
#              endpoint so aegis-brain.html can trigger the real okf_lint.py scan.
# version: 0.2.0
# authors: contributors
#
# Usage:
#   python3 kernel/serve_vault.py
#   python3 kernel/serve_vault.py --port 8080
from __future__ import annotations

import argparse
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

from okf_common import BRAIN_ROOT, VAULT_ROOT


class VaultHandler(SimpleHTTPRequestHandler):
    """
    intent: Serve the vault as static files and expose POST /api/lint.
    input: HTTP requests.
    output: static files or lint.json from okf_lint.py.
    role: development server for aegis-brain.
    side_effects: runs okf_lint.py on POST /api/lint.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(VAULT_ROOT), **kwargs)

    def do_GET(self) -> None:
        """
        intent: Serve aegis-brain.html by default when visiting root.
        """
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/aegis-brain.html")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self) -> None:
        """
        intent: Run vault lint or compile and return results.
        input: POST /api/lint or /api/compile.
        output: HTTP 200 + JSON body, or 4xx/5xx on failure.
        role: API handler.
        """
        if self.path == "/api/lint":
            self._handle_lint()
        elif self.path == "/api/compile":
            self._handle_compile()
        else:
            self.send_error(404, "not found")

    def _handle_lint(self) -> None:
        """
        intent: Run okf_lint.py and return lint.json.
        """
        # _log("[T-01] running okf_lint.py via /api/lint")
        try:
            proc = subprocess.run(
                [sys.executable, "kernel/okf_lint.py"],
                cwd=VAULT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                env={**dict(__import__("os").environ), "OKF_VAULT_ROOT": str(VAULT_ROOT)},
            )
            lint_path = BRAIN_ROOT / "lint.json"
            if not lint_path.exists():
                self.send_error(500, proc.stderr or "lint.json not produced")
                return
            payload = lint_path.read_text(encoding="utf-8")
            self._send_json(payload)
        except OSError as exc:
            self.send_error(500, f"[DBG-601] lint failed: {exc}")

    def _handle_compile(self) -> None:
        """
        intent: Run graph_compiler.py and return graph.json.
        """
        # _log("[T-02] running graph_compiler.py via /api/compile")
        try:
            proc = subprocess.run(
                [sys.executable, "kernel/graph_compiler.py"],
                cwd=VAULT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                env={**dict(__import__("os").environ), "OKF_VAULT_ROOT": str(VAULT_ROOT)},
            )
            graph_path = BRAIN_ROOT / "graph.json"
            if not graph_path.exists():
                self.send_error(500, proc.stderr or "graph.json not produced")
                return
            payload = graph_path.read_text(encoding="utf-8")
            self._send_json(payload)
        except OSError as exc:
            self.send_error(500, f"[DBG-602] compile failed: {exc}")

    def _send_json(self, payload: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, fmt: str, *args) -> None:
        """Suppress default request logging unless --verbose."""
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)


def main() -> int:
    """
    intent: CLI entry point — start the vault HTTP server.
    input: --host, --port, --verbose from argparse.
    output: process exit code (runs until interrupted).
    role: CLI entry point.
    side_effects: binds a TCP port and serves the vault.
    """
    parser = argparse.ArgumentParser(description="Serve aegis with /api/lint")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address (default: 127.0.0.1 — local only)",
    )
    parser.add_argument("--port", type=int, default=8080, help="listen port (default 8080)")
    parser.add_argument("--verbose", action="store_true", help="log each HTTP request")
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), VaultHandler)
    server.verbose = args.verbose
    print(f"[DBG-600] serving {VAULT_ROOT} at http://{args.host}:{args.port}/")
    print(f"[DBG-600] aegis-brain: http://{args.host}:{args.port}/aegis-brain.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DBG-600] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
