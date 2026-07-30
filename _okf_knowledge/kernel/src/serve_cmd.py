"""Local brain HTTP server."""
from __future__ import annotations

import ipaddress
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from src.compile_cmd import cmd_compile
from src.lint_cmd import build_lint_report
from src.paths import AEGIS_BRAIN_HTML, GRAPH_JSON, KERNEL_SRC, VAULT_ROOT
from src.vault import inject_into_aegis_brain

# Static files allowed for GET (no vault tree listing / exfil).
_STATIC_FILES: dict[str, Path] = {
    "/": AEGIS_BRAIN_HTML,
    "/aegis-brain.html": AEGIS_BRAIN_HTML,
    "/graph.json": GRAPH_JSON,
}


def _is_loopback(host: str) -> bool:
    """
    intent: Decide whether a client/bind address is loopback-only.
    input: host — IP or hostname string.
    output: True for localhost / loopback addresses.
    role: serve mutate-API gate.
    side_effects: none.
    """
    h = (host or "").strip().lower()
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def _origin_is_loopback(origin: str) -> bool:
    """
    intent: Allow browser Origin only when it points at loopback.
    input: Origin or Referer header value (may be empty).
    output: True when missing (non-browser/curl) or host is loopback.
    role: CSRF soft gate for mutate POSTs.
    side_effects: none.
    """
    raw = (origin or "").strip()
    if not raw:
        return True  # curl / non-browser clients
    try:
        host = urlparse(raw).hostname or ""
    except ValueError:
        return False
    return _is_loopback(host)


class VaultHandler(BaseHTTPRequestHandler):
    """
    intent: Serve only brain visualizer assets + loopback mutate APIs.
    input: HTTP requests.
    output: aegis-brain.html / graph.json, or lint/compile JSON.
    role: development server for aegis-brain (no vault static tree).
    side_effects: runs lint/compile on POST (loopback clients only).
    """

    def do_GET(self) -> None:
        """Serve allow-listed visualizer files only."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/aegis-brain.html")
            self.end_headers()
            return
        src_file = _STATIC_FILES.get(path)
        if src_file is None:
            self.send_error(404, "not found (vault files are not served)")
            return
        self._send_file(src_file)

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

    def _require_loopback_client(self) -> bool:
        """Reject mutate APIs unless the TCP peer is loopback."""
        peer = self.client_address[0] if self.client_address else ""
        if not _is_loopback(peer):
            self.send_error(403, "mutate APIs are loopback-only")
            return False
        origin = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if not _origin_is_loopback(origin):
            self.send_error(403, "mutate APIs require loopback Origin/Referer (or none)")
            return False
        return True

    def do_POST(self) -> None:
        """
        intent: Run vault lint or compile and return results (loopback only).
        input: POST /api/lint or /api/compile.
        output: HTTP 200 + JSON body, or 4xx/5xx on failure.
        role: API handler.
        """
        if not self._require_loopback_client():
            return
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
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)


def cmd_serve(args) -> int:
    """
    intent: Start the brain visualizer HTTP server (allow-listed GET only).
    input: parsed args (--host, --port, --verbose).
    output: process exit code (runs until interrupted).
    role: subcommand.
    side_effects: binds a TCP port; serves html/graph only.
    """
    if not _is_loopback(args.host):
        print(
            f"[DBG-600] refusing non-loopback bind {args.host!r} "
            "(use 127.0.0.1 / ::1; mutate APIs are local-only)",
            file=sys.stderr,
        )
        return 2
    server = HTTPServer((args.host, args.port), VaultHandler)
    server.verbose = args.verbose
    print(f"[DBG-600] serving visualizer (not vault tree) at http://{args.host}:{args.port}/")
    print(f"[DBG-600] aegis-brain: http://{args.host}:{args.port}/aegis-brain.html")
    print(f"[DBG-600] assets from {KERNEL_SRC} (brain root {VAULT_ROOT} not exposed)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DBG-600] stopped")
    return 0
