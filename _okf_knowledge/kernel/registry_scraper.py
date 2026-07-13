#!/usr/bin/env python3
# file_name: registry_scraper.py
# description: JIT upstream awareness — on a cache miss, fetch official docs
#              (GitHub Actions first) and write them back into the vault as an
#              OKF Reference concept. Stdlib only.
# version: 0.2.0
# authors: contributors
#
# Usage:
#   python3 kernel/registry_scraper.py "workflow syntax"
#   python3 kernel/registry_scraper.py "https://docs.github.com/en/actions/..."
from __future__ import annotations

import ipaddress
import re
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

from okf_common import VAULT_ROOT, format_frontmatter

# Keyword → (slug, title, url) catalog for GitHub Actions docs.
# Extend this table when adding new upstream sources (Terraform, Flux, ...).
# "understand github actions" is covered by concepts/github-actions/ — not cached here.
GHA_CATALOG: dict[str, tuple[str, str, str]] = {
    "workflow syntax": (
        "workflow-syntax",
        "Workflow syntax for GitHub Actions",
        "https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax",
    ),
    "metadata syntax": (
        "metadata-syntax",
        "Metadata syntax for composite/custom actions (action.yml)",
        "https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax",
    ),
    "contexts": (
        "contexts",
        "Contexts reference (github.*, env.*, secrets.*, ...)",
        "https://docs.github.com/en/actions/reference/workflows-and-actions/contexts",
    ),
    "expressions": (
        "expressions",
        "Expressions reference (${{ ... }} operators and functions)",
        "https://docs.github.com/en/actions/reference/workflows-and-actions/expressions",
    ),
    "reusable workflows": (
        "reusable-workflows",
        "Reusing workflows (workflow_call)",
        "https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows",
    ),
    "events": (
        "events",
        "Events that trigger workflows",
        "https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows",
    ),
    "permissions": (
        "permissions",
        "GITHUB_TOKEN authentication and permissions",
        "https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication",
    ),
}


class _TextExtractor(HTMLParser):
    """
    intent: Crude HTML→text conversion preserving headings and code blocks.
    input: HTML fed via feed().
    output: text lines accumulated in self.lines.
    role: parser for scraped doc pages.
    side_effects: none.
    """

    _SKIP = {"script", "style", "nav", "footer", "header", "svg"}
    _HEADINGS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### "}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._skip_depth = 0
        self._prefix = ""
        self._in_pre = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._HEADINGS:
            self._prefix = self._HEADINGS[tag]
        elif tag == "pre":
            self._in_pre = True
            self.lines.append("```")
        elif tag == "li":
            self._prefix = "- "

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "pre":
            self._in_pre = False
            self.lines.append("```")
        elif tag in self._HEADINGS or tag == "li":
            self._prefix = ""

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data if self._in_pre else data.strip()
        if text:
            self.lines.append(self._prefix + text)
            self._prefix = ""


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate redirect targets before following."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_fetch_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_fetch_url(url: str) -> None:
    """
    intent: Block non-public fetch targets (SSRF guard).
    input: url — candidate fetch/redirect URL.
    output: none.
    role: security gate.
    side_effects: raises SystemExit on blocked URLs.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SystemExit("[DBG-403] only http/https URLs are allowed")
    host = parsed.hostname
    if not host:
        raise SystemExit("[DBG-403] URL must have a hostname")
    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or lowered.endswith(".local"):
        raise SystemExit(f"[DBG-403] blocked host: {host}")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
            ip = ipaddress.ip_address(info[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise SystemExit(f"[DBG-403] blocked private/reserved address: {host}")
    except socket.gaierror as exc:
        raise SystemExit(f"[DBG-403] cannot resolve host {host}: {exc}") from exc


def fetch_page(url: str) -> str:
    """
    intent: Download one docs page and reduce it to markdown-ish text.
    input: url — page to fetch.
    output: extracted text.
    role: network fetcher.
    side_effects: outbound HTTP request.
    """
    # _log("[T-01] fetching upstream doc")
    _validate_fetch_url(url)
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    req = urllib.request.Request(url, headers={"User-Agent": "aegis-okf-scraper/0.1"})
    with opener.open(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    extractor = _TextExtractor()
    extractor.feed(html)
    text = "\n".join(extractor.lines)
    return re.sub(r"\n{3,}", "\n\n", text)


def resolve_query(query: str) -> tuple[str, str, str]:
    """
    intent: Map a free-text query (or a direct URL) to (slug, title, url).
    input: query — user query string.
    output: catalog entry tuple.
    role: router.
    side_effects: none.
    """
    if query.startswith(("http://", "https://")):
        slug = re.sub(r"[^a-z0-9]+", "-", query.rstrip("/").rsplit("/", 1)[-1].lower()).strip("-")
        return slug or "page", query, query
    q = query.lower()
    for keyword, entry in GHA_CATALOG.items():
        if keyword in q or all(w in q for w in keyword.split()):
            return entry
    known = ", ".join(sorted(GHA_CATALOG))
    raise SystemExit(
        f"[DBG-401] no catalog match for '{query}'. Known topics: {known}. "
        "You can also pass a direct URL."
    )


def write_reference(slug: str, title: str, url: str, content: str) -> Path:
    """
    intent: Write the scraped content as a conformant OKF Reference concept.
    input: slug/title/url — catalog entry; content — extracted doc text.
    output: path of the written file.
    role: vault writer.
    side_effects: creates/overwrites a file under vault/github-actions/.
    """
    # _log("[T-02] writing Reference concept")
    out_dir = VAULT_ROOT / "vault" / "github-actions"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    max_chars = 20_000  # keep cached pages agent-readable in one pass
    truncated = content[:max_chars]
    note = "\n\n*(truncated — see source_url for the full page)*" if len(content) > max_chars else ""
    safe_title = re.sub(r"\s+", " ", title).strip()
    fm = {
        "type": "Reference",
        "title": safe_title,
        "description": "Cached upstream documentation, fetched by registry_scraper.py.",
        "tags": ["github-actions", "upstream", "cached"],
        "timestamp": now,
        "source_url": url,
    }
    doc = (
        format_frontmatter(fm)
        + "\n### Common Usage\n\n"
        + f"**Official documentation:** [{safe_title}]({url})\n\n"
        + "See [Simplicity First](/standards/simplicity-first.md) and\n"
        + "[Metadata Headers](/standards/metadata-headers.md) for house rules.\n\n"
        + "### Syntax\n\n"
        + f"{truncated}{note}\n\n"
        + "### Supported Formats & Variants\n\n"
        + "Refer to the upstream page for version-specific variants.\n\n"
        + "# Citations\n\n"
        + f"[1] [{safe_title}]({url})\n"
    )
    out_path = out_dir / f"{slug}.md"
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    """
    intent: CLI entry point — resolve query, fetch, write back, remind about optimizer.
    input: argv — command-line args (query string).
    output: process exit code.
    role: CLI entry point.
    side_effects: network fetch + vault write.
    """
    if len(argv) != 2:
        print('usage: registry_scraper.py "<query or URL>"', file=sys.stderr)
        return 2
    slug, title, url = resolve_query(argv[1])
    try:
        content = fetch_page(url)
    except (URLError, OSError, TimeoutError) as exc:
        # _log("[T-03] fetch failed")
        print(f"[DBG-402] upstream fetch failed for {url}: {exc}", file=sys.stderr)
        return 1
    out_path = write_reference(slug, title, url, content)
    print(f"[DBG-400] cached {url} -> {out_path.relative_to(VAULT_ROOT)}")
    print("next: python3 kernel/cache_optimizer.py  (normalize + recompile index)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
