"""Local brain HTTP server."""
from __future__ import annotations

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import json

from src.compile_cmd import cmd_compile
from src.lint_cmd import build_lint_report
from src.paths import AEGIS_BRAIN_HTML, GRAPH_JSON, KERNEL_SRC, VAULT_ROOT
from src.vault import inject_into_aegis_brain


class VaultHandler(SimpleHTTPRequestHandler):
    """
    intent: Serve the vault as static files and expose POST /api/lint + /api/compile.
    input: HTTP requests.
    output: static files, or lint.json / graph.json regenerated in-process.
    role: development server for aegis-brain.
    side_effects: runs lint/compile on POST.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(VAULT_ROOT), **kwargs)

    def do_GET(self) -> None:
        """
        intent: Serve aegis-brain.html / graph.json from kernel/src/; vault otherwise.
        """
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/aegis-brain.html")
            self.end_headers()
            return
        if path in ("/aegis-brain.html", "/graph.json"):
            src_file = AEGIS_BRAIN_HTML if path.endswith(".html") else GRAPH_JSON
            self._send_file(src_file)
            return
        super().do_GET()

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, f"{path.name} not found under {KERNEL_SRC}")
            return
        data = path.read_bytes()
        ctype = "text/html; charset=utf-8" if path.suffix == ".html" else "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        """
        intent: Run vault lint or compile and return results.
        input: POST /api/lint or /api/compile.
        output: HTTP 200 + JSON body, or 4xx/5xx on failure.
        role: API handler.
        """
        if self.path == "/api/lint":
            try:
                report = build_lint_report()
                report_json = json.dumps(report, indent=2)
                inject_into_aegis_brain("lint-data", report_json)
                self._send_json(report_json)
            except OSError as exc:
                self.send_error(500, f"[DBG-601] lint failed: {exc}")
        elif self.path == "/api/compile":
            self._run_and_send(cmd_compile, GRAPH_JSON, "DBG-602", "compile")
        else:
            self.send_error(404, "not found")

    def _run_and_send(self, fn, artifact: Path, code: str, label: str) -> None:
        """
        intent: Run a kernel command in-process and return its artifact.
        input: fn — cmd_lint/cmd_compile; artifact — produced JSON path.
        output: HTTP response with the artifact contents.
        role: API helper.
        side_effects: whatever fn writes.
        """
        try:
            fn(None)
            if not artifact.exists():
                self.send_error(500, f"{artifact.name} not produced")
                return
            self._send_json(artifact.read_text(encoding="utf-8"))
        except OSError as exc:
            self.send_error(500, f"[{code}] {label} failed: {exc}")

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


def cmd_serve(args) -> int:
    """
    intent: Start the vault HTTP server.
    input: parsed args (--host, --port, --verbose).
    output: process exit code (runs until interrupted).
    role: subcommand.
    side_effects: binds a TCP port and serves the vault.
    """
    server = HTTPServer((args.host, args.port), VaultHandler)
    server.verbose = args.verbose
    print(f"[DBG-600] serving {VAULT_ROOT} at http://{args.host}:{args.port}/")
    print(f"[DBG-600] aegis-brain: http://{args.host}:{args.port}/aegis-brain.html")
    print(f"[DBG-600] graph/html from {KERNEL_SRC}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DBG-600] stopped")
    return 0
