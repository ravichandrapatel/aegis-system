"""Local brain HTTP server — read-only visualizer."""
from __future__ import annotations

import ipaddress
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from okf.paths import ASSETS_DIR, GRAPH_JSON, BRAIN_HTML, VAULT_ROOT

# Static files allowed for GET (no vault tree listing / exfil).
_STATIC_FILES: dict[str, Path] = {
    "/": BRAIN_HTML,
    "/okf-brain.html": BRAIN_HTML,
    "/brain.html": BRAIN_HTML,
    "/graph.json": GRAPH_JSON,
}


def _is_loopback(host: str) -> bool:
    """
    intent: Decide whether a bind address is loopback-only.
    input: host — IP or hostname string.
    output: True for localhost / loopback addresses.
    role: bind guard.
    side_effects: none.
    """
    h = (host or "").strip().lower()
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


class VaultHandler(BaseHTTPRequestHandler):
    """
    intent: Serve the brain visualizer assets, read-only.
    input: HTTP GET requests.
    output: okf-brain.html / graph.json.
    role: development server for okf-brain.
    side_effects: none — this server cannot modify the repository.
    """

    def do_GET(self) -> None:
        """Serve allow-listed visualizer files only."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/okf-brain.html")
            self.end_headers()
            return
        src_file = _STATIC_FILES.get(path)
        if src_file is None:
            self.send_error(404, "not found (vault files are not served)")
            return
        self._send_file(src_file)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, f"{path.name} not found under {ASSETS_DIR}")
            return
        data = path.read_bytes()
        ctype = "text/html; charset=utf-8" if path.suffix == ".html" else "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)


def cmd_serve(args) -> int:
    """
    intent: Start the read-only brain visualizer HTTP server.
    input: parsed args (--host, --port, --verbose).
    output: process exit code (runs until interrupted).
    role: subcommand.
    side_effects: binds a TCP port; serves html/graph only.

    There are no mutate endpoints, so there is nothing to authenticate. Run
    `okf.py compile` / `okf.py lint` from a shell to refresh the data.
    """
    if not _is_loopback(args.host):
        # graph.json embeds full document bodies, so a non-loopback bind would
        # publish the whole vault to the network. This is content containment,
        # not authentication.
        print(
            f"[DBG-600] refusing non-loopback bind {args.host!r} "
            "(use 127.0.0.1 / ::1; graph.json contains full vault content)",
            file=sys.stderr,
        )
        return 2
    server = HTTPServer((args.host, args.port), VaultHandler)
    server.verbose = args.verbose
    print(f"[DBG-600] serving read-only visualizer at http://{args.host}:{args.port}/")
    print(f"[DBG-600] okf-brain: http://{args.host}:{args.port}/okf-brain.html")
    print(f"[DBG-600] assets from {ASSETS_DIR} (brain root {VAULT_ROOT} not exposed)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DBG-600] stopped")
    return 0
