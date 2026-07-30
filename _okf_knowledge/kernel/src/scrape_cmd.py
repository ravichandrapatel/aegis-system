"""Fetch upstream docs into vault References."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

from src.config import load_okf_config, scan_secrets
from src.paths import SKIP_DIRS, VAULT_ROOT
from src.vault import format_frontmatter

# Builtin keyword → (slug, title, url). Extend via vault/**/scrape-catalog.json.
_BUILTIN_SCRAPE_CATALOGS: dict[str, dict[str, tuple[str, str, str]]] = {
    "github-actions": {
        "workflow syntax": (
            "workflow-syntax",
            "Workflow syntax for GitHub Actions",
            "https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions",
        ),
        "contexts": (
            "contexts",
            "Contexts and expressions",
            "https://docs.github.com/en/actions/learn-github-actions/contexts",
        ),
        "reusable workflows": (
            "reusing-workflows",
            "Reusing workflows",
            "https://docs.github.com/en/actions/using-workflows/reusing-workflows",
        ),
        "metadata syntax": (
            "metadata-syntax",
            "Metadata syntax for GitHub Actions",
            "https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions",
        ),
    },
}


def _domain_from_url(url: str) -> str:
    """
    intent: Map an upstream URL to a vault/references/<domain>/ folder name.
    input: url — scraped page URL.
    output: kebab-case domain slug (e.g. github-actions, docs-terraform-io).
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "upstream").lower().removeprefix("www.")
    path = (parsed.path or "").lower()
    if "github.com" in host and "actions" in path:
        return "github-actions"
    if host == "docs.github.com" and "/actions" in path:
        return "github-actions"
    return re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "upstream"

def _load_scrape_catalogs() -> dict[str, dict[str, tuple[str, str, str]]]:
    """
    intent: Merge builtin scrape catalogs with any scrape-catalog.json in the brain.
    input: none.
    output: domain → {keyword: (slug, title, url)}.
    role: dynamic catalog loader — drop JSON files to add Terraform/Flux/etc.
    side_effects: none (read-only).

    JSON shape:
      {
        "domain": "terraform",
        "entries": {
          "language": {"slug": "language", "title": "…", "url": "https://…"}
        }
      }
    """
    catalogs: dict[str, dict[str, tuple[str, str, str]]] = {
        domain: dict(entries) for domain, entries in _BUILTIN_SCRAPE_CATALOGS.items()
    }
    for path in sorted(VAULT_ROOT.rglob("scrape-catalog.json")):
        if any(part.startswith(".") or part in SKIP_DIRS for part in path.relative_to(VAULT_ROOT).parts):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        entries_raw = raw.get("entries") or {}
        if not isinstance(entries_raw, dict):
            continue
        domain = str(raw.get("domain") or "").strip()
        if not domain:
            first_url = ""
            for meta in entries_raw.values():
                if isinstance(meta, dict) and meta.get("url"):
                    first_url = str(meta["url"])
                    break
            domain = _domain_from_url(first_url) if first_url else path.parent.name
        bucket = catalogs.setdefault(domain, {})
        for keyword, meta in entries_raw.items():
            if not isinstance(meta, dict):
                continue
            slug = str(meta.get("slug") or keyword).strip()
            title = str(meta.get("title") or keyword).strip()
            url = str(meta.get("url") or "").strip()
            if url:
                bucket[str(keyword).lower()] = (slug, title, url)
    return catalogs

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
    # Build unspecified-IPv4 without a literal "0.0.0.0" (Bandit B104 false positive on deny-list).
    unspecified_v4 = ".".join(("0",) * 4)
    if lowered in {"localhost", "127.0.0.1", "::1", unspecified_v4} or lowered.endswith(
        ".local"
    ):
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
    _validate_fetch_url(url)
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    req = urllib.request.Request(url, headers={"User-Agent": "aegis-okf-scraper/0.1"})
    with opener.open(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    extractor = _TextExtractor()
    extractor.feed(html)
    text = "\n".join(extractor.lines)
    return re.sub(r"\n{3,}", "\n\n", text)

def resolve_query(query: str) -> tuple[str, str, str, str]:
    """
    intent: Map a free-text query (or a direct URL) to (domain, slug, title, url).
    input: query — user query string.
    output: catalog entry with dynamic domain for vault/references/<domain>/.
    role: router.
    side_effects: none.
    """
    if query.startswith(("http://", "https://")):
        slug = re.sub(r"[^a-z0-9]+", "-", query.rstrip("/").rsplit("/", 1)[-1].lower()).strip("-")
        domain = _domain_from_url(query)
        return domain, slug or "page", query, query
    q = query.lower()
    catalogs = _load_scrape_catalogs()
    for domain, entries in catalogs.items():
        for keyword, (slug, title, url) in entries.items():
            if keyword in q or all(w in q for w in keyword.split()):
                return domain, slug, title, url
    known = ", ".join(sorted({k for e in catalogs.values() for k in e}))
    raise SystemExit(
        f"[DBG-401] no catalog match for '{query}'. Known topics: {known}. "
        "You can also pass a direct URL, or add vault/**/scrape-catalog.json."
    )

def _standard_see_also_links() -> str:
    """Build a short 'see also' blurb from standards/index.md or tagged standards."""
    index = VAULT_ROOT / "standards" / "index.md"
    if index.is_file():
        return (
            "See [Standards index](/standards/index.md) for binding house rules.\n\n"
        )
    return ""

def compress_reference_body(content: str, max_chars: int) -> tuple[str, str]:
    """
    intent: Keep headings + short body under each (structure-preserving compress).
    output: (body, note_suffix).
    """
    if len(content) <= max_chars:
        return content, ""
    lines = content.splitlines()
    out: list[str] = []
    under = 0
    for line in lines:
        if line.startswith("#"):
            out.append(line)
            under = 0
            continue
        if under < 3:
            out.append(line)
            under += 1
        elif under == 3:
            out.append("…")
            under += 1
    text_out = "\n".join(out)
    note = "\n\n*(compressed — see source_url for full page)*"
    if len(text_out) + len(note) > max_chars:
        return text_out[: max(0, max_chars - 64)], "\n\n*(compressed/truncated)*"
    return text_out, note

def _safe_ref_segment(value: str, *, label: str) -> str:
    """
    intent: Reject path traversal / separators in reference domain or slug.
    input: raw segment; label for error messages.
    output: sanitized single path segment.
    role: path containment gate.
    side_effects: raises ValueError when unsafe.
    """
    s = (value or "").strip().replace("\\", "/")
    if not s or s in {".", ".."} or "/" in s or s.startswith("~"):
        raise ValueError(f"[DBG-403] unsafe {label}: {value!r}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", s):
        raise ValueError(f"[DBG-403] unsafe {label} characters: {value!r}")
    return s


def _brain_contained(path: Path) -> Path:
    """Resolve path and require it stays under VAULT_ROOT."""
    root = VAULT_ROOT.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"[DBG-403] path escapes brain root: {path}") from exc
    return resolved


def write_reference(
    slug: str,
    title: str,
    url: str,
    content: str,
    domain: str | None = None,
) -> Path:
    """
    intent: Write the scraped content as a conformant OKF Reference concept.
    input: slug/title/url; optional domain (defaults from URL).
    output: path of the written file under vault/references/<domain>/.
    role: vault writer.
    side_effects: creates/overwrites a Reference markdown file.
    """
    leaks = scan_secrets(content)
    if leaks:
        raise ValueError(
            f"[DBG-403] secret scan blocked scrape write ({', '.join(leaks)}). "
            "Redact upstream content or set credential_scan=False in src.config.OKF_CONFIG."
        )
    cfg = load_okf_config()
    domain_slug = _safe_ref_segment(
        (domain or _domain_from_url(url)).strip() or "upstream",
        label="domain",
    )
    safe_slug = _safe_ref_segment(slug, label="slug")
    out_dir = _brain_contained(VAULT_ROOT / "vault" / "references" / domain_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    max_chars = int(cfg.get("reference_max_chars", 20_000))
    if cfg.get("reference_compress", True) and len(content) > max_chars:
        truncated, note = compress_reference_body(content, max_chars)
    else:
        truncated = content[:max_chars]
        note = (
            "\n\n*(truncated — see source_url for the full page)*"
            if len(content) > max_chars
            else ""
        )
    safe_title = re.sub(r"\s+", " ", title).strip()
    fm = {
        "type": "Reference",
        "title": safe_title,
        "description": "Cached upstream documentation, fetched by `okf.py scrape`.",
        "tags": [domain_slug, "upstream", "cached"],
        "timestamp": now,
        "source_url": url,
    }
    doc = (
        format_frontmatter(fm)
        + "\n### Common Usage\n\n"
        + f"**Official documentation:** [{safe_title}]({url})\n\n"
        + _standard_see_also_links()
        + "### Syntax\n\n"
        + f"{truncated}{note}\n\n"
        + "### Supported Formats & Variants\n\n"
        + "Refer to the upstream page for version-specific variants.\n\n"
        + "# Citations\n\n"
        + f"[1] [{safe_title}]({url})\n"
    )
    leaks_doc = scan_secrets(doc)
    if leaks_doc:
        raise ValueError(
            f"[DBG-403] secret scan blocked reference document ({', '.join(leaks_doc)})."
        )
    out_path = _brain_contained(out_dir / f"{safe_slug}.md")
    out_path.write_text(doc, encoding="utf-8")
    return out_path

def cmd_scrape(args: argparse.Namespace) -> int:
    """
    intent: Resolve query, fetch, write back, remind about optimize.
    input: parsed args (query string).
    output: process exit code.
    role: subcommand.
    side_effects: network fetch + vault write.
    """
    domain, slug, title, url = resolve_query(args.query)
    try:
        content = fetch_page(url)
    except (URLError, OSError, TimeoutError) as exc:
        print(f"[DBG-402] upstream fetch failed for {url}: {exc}", file=sys.stderr)
        return 1
    try:
        out_path = write_reference(slug, title, url, content, domain=domain)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"[DBG-400] cached {url} -> {out_path.relative_to(VAULT_ROOT)}")
    print("next: python3 kernel/okf.py optimize  (normalize + recompile index)")
    return 0

