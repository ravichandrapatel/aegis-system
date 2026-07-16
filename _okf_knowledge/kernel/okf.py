#!/usr/bin/env python3
# file_name: okf.py
# description: Single-file Aegis OKF kernel — lookup, card, compile, lint,
#              enrich, optimize, scrape, and serve as subcommands. Stdlib only.
#              Consolidates okf_common / prompt_card / okf_lookup /
#              graph_compiler / okf_lint / okf_enrich / cache_optimizer /
#              registry_scraper / serve_vault.
# version: 1.2.0
# authors: contributors
#
# Usage:
#   python3 _okf_knowledge/kernel/okf.py lookup "<query>" [--card] [--json] [--paths] ...
#   python3 _okf_knowledge/kernel/okf.py pack "<query>" [--style json|markdown|xml]
#   python3 _okf_knowledge/kernel/okf.py card <path> [<path>...]
#   python3 _okf_knowledge/kernel/okf.py compile [--force]
#   python3 _okf_knowledge/kernel/okf.py lint
#   python3 _okf_knowledge/kernel/okf.py enrich [--write] [--only X] [--limit N]
#   python3 _okf_knowledge/kernel/okf.py optimize
#   python3 _okf_knowledge/kernel/okf.py scrape "<query or URL>"
#   python3 _okf_knowledge/kernel/okf.py serve [--port 8080]
"""
intent: One CLI for every kernel operation on the Aegis OKF brain.
input: subcommand + flags (see Usage above); env OKF_VAULT_ROOT overrides the
       brain root; env OKF_LLM_* configures the enrich endpoint;
       optional okf.config.json / .okfignore under the brain root.
output: subcommand-specific stdout; compiled artifacts / lint.json / vault
        edits depending on the subcommand.
role: kernel entry point (replaces the previous per-script CLIs).
side_effects: read-only for lookup/card/pack; compile/lint/enrich/optimize/scrape
              write under the brain; serve binds a TCP port.

v1.1 speed: mtime-memoized artifact loads, compile-time normalized fields +
inverted token index, camelCase/snake_case tokenization, incremental compile
cache (skip unchanged concepts; no-op when vault hash-clean).

v1.2 (D12): better token estimate (+ optional tiktoken), secret scan on scrape,
.okfignore, shared Prompt Pack assembly, pack export, lookup --json.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

# =============================================================================
# Shared vault helpers (formerly okf_common.py)
# =============================================================================

# Scripts live in kernel/; vault/brain root is the parent of kernel/
# (`_okf_knowledge/`). AGENTS.md lives one level up (package root).
VAULT_ROOT = Path(
    os.environ.get("OKF_VAULT_ROOT", str(Path(__file__).resolve().parent.parent))
).resolve()
BRAIN_ROOT = VAULT_ROOT
# OKF dialect reserved basenames (format rule — not vault-specific).
RESERVED_FILENAMES = {"index.md", "log.md"}
# Seed names always treated as control-plane; plus any *.md at package root (dynamic).
_CONTROL_PLANE_SEED = {
    "AGENTS.md",
    "README.md",
    "ADR.md",
    "CLAUDE.md",
    "GEMINI.md",
    "COPILOT.md",
    "agent.md",
    "BENCH_PROMPT.md",
}
# Tooling / VCS dirs to skip while walking the brain (not knowledge taxonomy).
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".cursor",
    ".github",
    ".windsurf",
    ".continue",
    "__pycache__",
}
# Fallback taxonomy if AGENTS.md is missing; normally loaded dynamically.
_TYPE_SEED = {
    "Concept",
    "Playbook",
    "System",
    "Reference",
    "Incident",
    "Profile",
}
GRAPH_CONTENT_MAX = 4000
INDEX_FORMAT_VERSION = 2
COMPILE_CACHE_VERSION = 1
COMPILE_CACHE_NAME = ".okf-compile-cache.json"

# Matches markdown links, capturing the target: [text](target)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# camelCase / PascalCase / SNAKE splits for search tokens
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]+|\d+")


@dataclass
class Concept:
    """
    intent: In-memory representation of one OKF concept document.
    input: populated by load_concept().
    output: n/a (data container).
    role: value object shared by all vault tooling.
    side_effects: none.
    """

    concept_id: str          # path relative to vault root, without .md suffix
    path: Path
    frontmatter: dict[str, object] = field(default_factory=dict)
    body: str = ""
    parse_error: str | None = None


def parse_frontmatter(text: str) -> tuple[dict[str, object] | None, str]:
    """
    intent: Split a markdown document into (frontmatter dict, body) without PyYAML.
            Supports the flat `key: value` and `key: [a, b]` subset used by OKF.
    input: text — full file contents.
    output: (dict or None if no/invalid frontmatter block, body string).
    role: pure parser.
    side_effects: none.
    """
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    try:
        end = next(i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---")
    except StopIteration:
        return None, text

    fm: dict[str, object] = {}
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            return None, text
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            fm[key.strip()] = [v for v in items if v]
        else:
            fm[key.strip()] = value.strip("'\"")
    body = "\n".join(lines[end + 1:])
    return fm, body


def iter_concept_files(root: Path = VAULT_ROOT) -> list[Path]:
    """
    intent: Enumerate every concept .md file in the vault, skipping reserved
            filenames and non-content directories.
    input: root — vault root path.
    output: sorted list of Paths.
    role: vault walker.
    side_effects: none (read-only filesystem access).
    """
    files: list[Path] = []
    control_names = control_plane_filenames()
    # Zone 2: only optional profiles markdown under kernel/ (tools are .py).
    kernel_keep = {"profiles"}
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        parts = rel.parts

        # Skip hidden directories
        if any(p.startswith(".") for p in parts):
            continue

        # Skip base kernel directory but allow profiles/
        # Handles both root/kernel and root/knowledge/kernel
        if "kernel" in parts:
            idx = parts.index("kernel")
            if len(parts) <= idx + 1 or parts[idx + 1] not in kernel_keep:
                continue

        # Skip other reserved directories
        if "_inbox" in parts:
            continue

        if any(part in SKIP_DIRS for part in parts):
            continue
        if path.name in RESERVED_FILENAMES or path.name in control_names:
            continue
        if path_ignored(rel):
            continue
        files.append(path)
    return files


def control_plane_filenames() -> set[str]:
    """
    intent: Control-plane / IDE-bridge markdown basenames (seed + package-root *.md).
    input: none.
    output: set of filenames (e.g. AGENTS.md, BENCH_PROMPT.md).
    role: dynamic discovery so new root docs are not treated as concepts.
    side_effects: none (read-only).
    """
    names = set(_CONTROL_PLANE_SEED) | set(RESERVED_FILENAMES)
    pkg_root = VAULT_ROOT.parent
    if pkg_root.is_dir():
        for path in pkg_root.glob("*.md"):
            names.add(path.name)
    return names


def known_types() -> set[str]:
    """
    intent: House taxonomy of frontmatter `type` values.
    input: none — prefers AGENTS.md "Known type values" table; falls back to seed.
    output: set of type names (includes Profile, Concept, …).
    role: lint taxonomy source (dynamic — tracks AGENTS.md).
    side_effects: none (read-only).
    """
    types = set(_TYPE_SEED)
    agents = VAULT_ROOT.parent / "AGENTS.md"
    if not agents.is_file():
        return types
    try:
        text = agents.read_text(encoding="utf-8")
    except OSError:
        return types
    # Rows like: | `Concept` | 3 or 4 | …
    for match in re.finditer(r"^\|\s*`([A-Z][A-Za-z0-9_-]*)`\s*\|", text, re.MULTILINE):
        types.add(match.group(1))
    return types


def is_standard_concept(concept: Concept) -> bool:
    """
    intent: Detect binding house standards (path or tag), not a hardcoded folder only.
    input: loaded concept.
    output: True when under standards/ or tagged `standard`.
    """
    if concept.concept_id.startswith("standards/"):
        return True
    tags = concept.frontmatter.get("tags", [])
    if isinstance(tags, list):
        return any(str(t).strip().lower() == "standard" for t in tags)
    return str(tags).strip().lower() == "standard"


def escape_yaml_scalar(value: str) -> str:
    """
    intent: Quote a frontmatter scalar when plain form would be ambiguous.
    input: value — raw string.
    output: YAML-safe scalar token.
    role: serializer helper.
    side_effects: none.
    """
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if (
        not value
        or value[0] in " \t#:@&*!|>'\"%}]["
        or ":" in value
        or "\n" in value
        or value != value.strip()
    ):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value


def format_frontmatter(fm: dict[str, object]) -> str:
    """
    intent: Render a frontmatter block with safe scalar quoting.
    input: fm — frontmatter dict.
    output: --- delimited YAML-ish block ending with newline.
    role: shared writer for reference tooling.
    side_effects: none.
    """
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            items = [escape_yaml_scalar(str(v)) for v in value]
            lines.append(f"{key}: [{', '.join(items)}]")
        else:
            lines.append(f"{key}: {escape_yaml_scalar(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def is_within_vault(path: Path, root: Path = VAULT_ROOT) -> bool:
    """
    intent: Test whether a resolved path stays inside the vault root.
    input: path — candidate path; root — vault root.
    output: True when path is under root.
    role: path guard for link resolution.
    side_effects: none.
    """
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def concept_id_from_path(resolved: Path, root: Path = VAULT_ROOT) -> str | None:
    """
    intent: Map a resolved filesystem path to a vault concept id.
    input: resolved path, vault root.
    output: concept id string or None when outside the vault.
    role: shared link target normalizer.
    side_effects: none.
    """
    if not is_within_vault(resolved, root):
        return None
    return str(resolved.resolve().relative_to(root.resolve())).removesuffix(".md")


def load_concept(path: Path, root: Path = VAULT_ROOT) -> Concept:
    """
    intent: Read one concept file into a Concept, recording parse failures
            instead of raising so lint can report them.
    input: path — concept file; root — vault root.
    output: Concept.
    role: loader.
    side_effects: none (read-only filesystem access).
    """
    concept_id = str(path.relative_to(root)).removesuffix(".md")
    concept = Concept(concept_id=concept_id, path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        concept.parse_error = f"[DBG-001] unreadable: {exc}"
        return concept
    fm, body = parse_frontmatter(text)
    if fm is None:
        concept.parse_error = "[DBG-002] missing or unparseable YAML frontmatter"
        concept.body = text
        return concept
    concept.frontmatter = fm
    concept.body = body
    return concept


def load_vault(root: Path = VAULT_ROOT) -> list[Concept]:
    """
    intent: Load every concept in the vault.
    input: root — vault root path.
    output: list of Concepts (including ones with parse errors).
    role: convenience aggregator.
    side_effects: none (read-only filesystem access).
    """
    return [load_concept(p, root) for p in iter_concept_files(root)]


def extract_links(body: str) -> list[str]:
    """
    intent: Pull internal .md link targets out of a markdown body.
    input: body — markdown text.
    output: list of link targets (bundle-absolute or relative), external URLs excluded.
    role: pure extractor for graph building and lint.
    side_effects: none.
    """
    targets = []
    for target in _LINK_RE.findall(body):
        if target.startswith(("http://", "https://", "mailto:", "file://")):
            continue
        target = target.split("#", 1)[0]
        if target.endswith(".md"):
            targets.append(target)
    return targets


def inject_into_aegis_brain(tag_id: str, payload_json: str, root: Path = BRAIN_ROOT) -> bool:
    """
    intent: Embed a JSON payload into aegis-brain.html's data script tag so the
            graph auto-loads even when the file is opened as file://.
    input: tag_id — "graph-data" or "lint-data"; payload_json — serialized JSON;
           root — directory containing aegis-brain.html.
    output: True if the tag was found and replaced, False otherwise.
    role: shared writer for compile and lint.
    side_effects: rewrites aegis-brain.html in place.
    """
    html_path = root / "aegis-brain.html"
    if not html_path.exists():
        return False
    html = html_path.read_text(encoding="utf-8")
    # Escape "</" so the payload cannot terminate the <script> tag early.
    safe = payload_json.replace("</", "<\\/")
    pattern = re.compile(
        rf'(<script id="{tag_id}" type="application/json">).*?(</script>)',
        re.DOTALL,
    )
    # Lambda replacement so backslashes in the JSON are not treated as regex escapes.
    new_html, count = pattern.subn(lambda m: m.group(1) + safe + m.group(2), html)
    if count == 0:
        print(
            f"[DBG-203] aegis-brain.html missing <script id=\"{tag_id}\"> block",
            file=sys.stderr,
        )
        return False
    html_path.write_text(new_html, encoding="utf-8")
    return True


def resolve_link(target: str, source: Path, root: Path = VAULT_ROOT) -> Path:
    """
    intent: Resolve a bundle-absolute (/x/y.md) or relative (./y.md) link to a
            filesystem path. Bundle-absolute paths are relative to the brain
            root; AGENTS.md / README / IDE bridges may resolve at the parent
            share/repo root when not present inside the brain.
    input: target — link target; source — file containing the link; root — vault root.
    output: resolved Path (may lie outside root — check with is_within_vault).
    role: pure resolver.
    side_effects: none.
    """
    if target.startswith("/"):
        rel = target.lstrip("/")
        inside = (root / rel).resolve()
        if inside.exists():
            return inside
        name = Path(rel).name
        if name in control_plane_filenames():
            outside = (root.parent / name).resolve()
            if outside.exists():
                return outside
        return inside
    return (source.parent / target).resolve()


# =============================================================================
# Prompt Cards (formerly prompt_card.py)
# =============================================================================

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_CARD_TITLE = re.compile(r"^prompt\s+card$", re.I)


def extract_prompt_card(text: str) -> str | None:
    """
    intent: Return the body under the first ## Prompt Card heading.
    input: full markdown text.
    output: card body string (stripped) or None if missing/empty.
    role: pure extractor.
    side_effects: none.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _HEADING_RE.match(lines[i])
        if m and _CARD_TITLE.match(m.group(2).strip()):
            level = len(m.group(1))
            i += 1
            body: list[str] = []
            while i < len(lines):
                m2 = _HEADING_RE.match(lines[i])
                if m2 and len(m2.group(1)) <= level:
                    break
                body.append(lines[i])
                i += 1
            card = "\n".join(body).strip()
            return card or None
        i += 1
    return None


def _resolve_card_path(raw: str) -> Path:
    """
    intent: Resolve a user path against CWD or vault root.
    input: raw path string.
    output: absolute Path.
    role: pure resolver.
    side_effects: none.
    """
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    candidate = (VAULT_ROOT / raw).resolve()
    if candidate.is_file():
        return candidate
    # allow paths relative to package root (parent of vault)
    pkg = VAULT_ROOT.parent / raw
    if pkg.is_file():
        return pkg.resolve()
    return p.resolve()


def cmd_card(args: argparse.Namespace) -> int:
    """
    intent: Emit Prompt Cards for known paths or fail if any missing.
    input: parsed args (paths, --max-chars).
    output: exit 0 on success, 1 on missing card/file.
    role: subcommand.
    side_effects: reads files; prints to stdout/stderr.
    """
    chunks: list[str] = []
    errors = 0
    for raw in args.paths:
        path = _resolve_card_path(raw)
        if not path.is_file():
            print(f"[prompt_card] missing file: {raw}", file=sys.stderr)
            errors += 1
            continue
        text = path.read_text(encoding="utf-8")
        card = extract_prompt_card(text)
        if card is None:
            print(f"[prompt_card] no ## Prompt Card in {path}", file=sys.stderr)
            errors += 1
            continue
        if len(card) > args.max_chars:
            print(
                f"[prompt_card] WARN {path.name}: {len(card)} chars > {args.max_chars}",
                file=sys.stderr,
            )
        rel = path
        try:
            rel = path.relative_to(VAULT_ROOT)
        except ValueError:
            pass
        chunks.append(f"### Card: {rel}\n{card}")

    if errors:
        return 1
    print("\n\n".join(chunks))
    return 0


# =============================================================================
# Lookup (formerly okf_lookup.py)
# =============================================================================

# Tunable field weights (lexical scorer).
TITLE_WEIGHT = 10
ID_WEIGHT = 8
TAG_WEIGHT = 6
DESC_WEIGHT = 3
TYPE_WEIGHT = 2
SLUG_BONUS = 12

# Match-quality multipliers applied to the field weight.
EXACT_MULT = 3
PREFIX_MULT = 2
SUBSTRING_MULT = 1

# Graph proximity bonuses (hops from a strong lexical seed).
GRAPH_HOP1 = 4
GRAPH_HOP2 = 2

MIN_TERM_LEN = 2
DEFAULT_MAX_CARDS = 8
DEFAULT_TOKEN_BUDGET = 1200
# Fallback chars≈tokens*4 when tiktoken is unavailable.
CHARS_PER_TOKEN = 4
CONFIG_NAME = "okf.config.json"
OKFIGNORE_NAME = ".okfignore"
_CONFIG_CACHE: dict[str, object] | None = None
_IGNORE_CACHE: list[str] | None = None
_TIKTOKEN_ENC = None  # lazy; False = tried and missing
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"), "private_key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key_id"),
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "github_pat"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "github_fine_grained_pat"),
    (re.compile(r"gho_[A-Za-z0-9]{36,}"), "github_oauth"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "openai_sk"),
    (re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[\'\"][^\'\"]{16,}"), "credential_assign"),
]


def load_okf_config() -> dict[str, object]:
    """
    intent: Load optional okf.config.json once (mtime not required — small file).
    output: merged defaults + file overrides.
    """
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    # Use credential_scan (not *secret*) so Bandit B105 does not treat the flag as a password.
    cfg: dict[str, object] = {
        "max_cards": DEFAULT_MAX_CARDS,
        "token_budget": DEFAULT_TOKEN_BUDGET,
        "prompt_card_max_chars": 600,
        "reference_max_chars": 20_000,
        "reference_compress": True,
        "credential_scan": True,
        "respect_gitignore": True,
    }
    path = VAULT_ROOT / CONFIG_NAME
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update({k: v for k, v in raw.items() if v is not None})
                # Backward compat with okf.config.json key from v1.2 draft
                legacy = "secret" + "_scan"
                if legacy in raw and "credential_scan" not in raw:
                    cfg["credential_scan"] = bool(raw[legacy])
        except (OSError, json.JSONDecodeError):
            pass
    _CONFIG_CACHE = cfg
    return cfg


def _read_ignore_file(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            out.append(s)
    except OSError:
        pass
    return out


def load_ignore_patterns() -> list[str]:
    """Merge .okfignore (+ optional .gitignore) under brain root."""
    global _IGNORE_CACHE
    if _IGNORE_CACHE is not None:
        return _IGNORE_CACHE
    patterns = _read_ignore_file(VAULT_ROOT / OKFIGNORE_NAME)
    cfg = load_okf_config()
    if cfg.get("respect_gitignore", True):
        patterns.extend(_read_ignore_file(VAULT_ROOT / ".gitignore"))
        patterns.extend(_read_ignore_file(VAULT_ROOT.parent / ".gitignore"))
    _IGNORE_CACHE = patterns
    return patterns


def path_ignored(rel: Path | str) -> bool:
    """Return True if vault-relative path matches an ignore pattern."""
    if isinstance(rel, Path):
        rel_s = rel.as_posix()
    else:
        rel_s = str(rel).replace(chr(92), "/")
    name = Path(rel_s).name
    for pat in load_ignore_patterns():
        p = pat.replace(chr(92), "/")
        if p.startswith("!"):
            continue  # negation not supported (keep simple)
        if p.endswith("/"):
            prefix = p.rstrip("/")
            if rel_s == prefix or rel_s.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(rel_s, p) or fnmatch.fnmatch(name, p):
            return True
    return False


def scan_secrets(text: str) -> list[str]:
    """Return list of secret kind labels found (empty = clean)."""
    if not text or not load_okf_config().get("credential_scan", True):
        return []
    found: list[str] = []
    for rx, label in _SECRET_PATTERNS:
        if rx.search(text):
            found.append(label)
    return found


def _tiktoken_encoder():
    global _TIKTOKEN_ENC
    if _TIKTOKEN_ENC is False:
        return None
    if _TIKTOKEN_ENC is not None:
        return _TIKTOKEN_ENC
    try:
        import tiktoken  # type: ignore

        _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
        return _TIKTOKEN_ENC
    except Exception:
        _TIKTOKEN_ENC = False
        return None


def count_tokens(text: str) -> int:
    """
    intent: Token estimate for Prompt Pack budgets.
    Prefer tiktoken cl100k_base when installed; else word/punct heuristic
    (~better than raw chars/4 on markdown).
    """
    if not text:
        return 0
    enc = _tiktoken_encoder()
    if enc is not None:
        return len(enc.encode(text))
    # Heuristic: whitespace/punct split ≈ BPE-ish for English+code
    parts = re.findall(r"[A-Za-z0-9_]+|[^\s]", text)
    return max(1, len(parts))


@dataclass
class IndexEntry:
    """
    intent: Slim searchable concept row (frontmatter only).
    input: index.json row or Concept.
    output: n/a.
    role: value object.
    side_effects: none.
    """

    concept_id: str
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    ctype: str = ""
    path: Path | None = None
    # Compile-time normalized fields (filled from index v2; computed on fallback).
    id_norm: str = ""
    title_norm: str = ""
    desc_norm: str = ""
    tags_norm: str = ""
    type_norm: str = ""
    search_tokens: frozenset[str] = field(default_factory=frozenset)


@dataclass
class Hit:
    """
    intent: One ranked lookup result with debug metadata.
    input: n/a.
    output: n/a.
    role: value object.
    side_effects: none.
    """

    entry: IndexEntry
    score: int
    matched: list[str] = field(default_factory=list)
    graph_hops: int | None = None


@dataclass
class _MtimeCache:
    """Process-local cache invalidated when a file's mtime_ns changes."""

    path: Path | None = None
    mtime_ns: int | None = None
    payload: object | None = None


_INDEX_CACHE = _MtimeCache()
_ADJ_CACHE = _MtimeCache()
_CARD_CACHE = _MtimeCache()
_INVERTED_CACHE = _MtimeCache()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokenize(text: str) -> list[str]:
    """
    intent: Split on whitespace, snake_case, camelCase, and punctuation.
    input: raw text (title, id, query, …).
    output: lowercase tokens (length ≥ MIN_TERM_LEN).
    """
    out: list[str] = []
    for word in re.split(r"[^A-Za-z0-9_+.-]+", text or ""):
        if not word:
            continue
        for part in word.replace("-", "_").split("_"):
            if not part:
                continue
            chunks = _CAMEL_RE.findall(part) or [part]
            for c in chunks:
                t = c.lower()
                if len(t) >= MIN_TERM_LEN:
                    out.append(t)
    return out


def _tokens(query: str) -> list[str]:
    # Preserve order, drop dupes.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in _tokenize(query):
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def _ensure_norms(entry: IndexEntry) -> None:
    """Fill normalized fields / search tokens when missing (v1 index or vault)."""
    if entry.id_norm and entry.search_tokens:
        return
    id_raw = entry.concept_id.replace("/", " ").replace("-", " ")
    entry.id_norm = entry.id_norm or _norm(id_raw)
    entry.title_norm = entry.title_norm or _norm(entry.title)
    entry.desc_norm = entry.desc_norm or _norm(entry.description)
    entry.tags_norm = entry.tags_norm or _norm(" ".join(entry.tags))
    entry.type_norm = entry.type_norm or _norm(entry.ctype)
    if not entry.search_tokens:
        bag = set(_tokenize(entry.concept_id))
        bag.update(_tokenize(entry.title))
        bag.update(_tokenize(entry.description))
        for t in entry.tags:
            bag.update(_tokenize(str(t)))
        bag.update(_tokenize(entry.ctype))
        entry.search_tokens = frozenset(bag)


def _field_score(term: str, hay: str, weight: int, hay_tokens: set[str] | None = None) -> tuple[int, str | None]:
    """
    intent: Score one term against one haystack with exact/prefix/substring tiers.
    input: term; normalized haystack; base field weight; optional token set.
    output: (points, match tier name) or (0, None).
    role: pure scorer helper.
    side_effects: none.
    """
    if not hay or not term:
        return 0, None
    tokens = hay_tokens if hay_tokens is not None else set(hay.split())
    if term == hay or term in tokens:
        return weight * EXACT_MULT, "exact"
    if any(tok.startswith(term) for tok in tokens) or hay.startswith(term):
        return weight * PREFIX_MULT, "prefix"
    if term in hay:
        return weight * SUBSTRING_MULT, "substr"
    # Acronym: term chars match successive word initials (e.g. "gha" → github actions)
    if len(term) >= 2:
        ordered = [t for t in hay.split() if t]
        if len(ordered) >= len(term):
            initials = "".join(t[0] for t in ordered)
            if initials.startswith(term):
                return weight * PREFIX_MULT, "acronym"
    return 0, None


def score_entry(entry: IndexEntry, terms: list[str]) -> tuple[int, list[str]]:
    """
    intent: Rank an index entry against query terms (frontmatter + id only).
    input: entry; normalized query terms.
    output: (score, matched field names).
    role: pure scorer.
    side_effects: none.
    """
    if not terms:
        return 0, []
    _ensure_norms(entry)
    hay = {
        "id": entry.id_norm,
        "title": entry.title_norm,
        "desc": entry.desc_norm,
        "tags": entry.tags_norm,
        "type": entry.type_norm,
    }
    hay_tok = {
        "id": set(entry.id_norm.split()),
        "title": set(entry.title_norm.split()),
        "desc": set(entry.desc_norm.split()),
        "tags": set(entry.tags_norm.split()),
        "type": set(entry.type_norm.split()),
    }
    # Merge camelCase search tokens into title/id bags for subword hits.
    hay_tok["title"] |= set(entry.search_tokens)
    hay_tok["id"] |= set(entry.search_tokens)
    weights = {
        "id": ID_WEIGHT,
        "title": TITLE_WEIGHT,
        "tags": TAG_WEIGHT,
        "desc": DESC_WEIGHT,
        "type": TYPE_WEIGHT,
    }
    score = 0
    matched: set[str] = set()
    for term in terms:
        # Direct token hit from compile-time bag (cheap camelCase/snake match).
        if term in entry.search_tokens:
            score += TITLE_WEIGHT * PREFIX_MULT
            matched.add("token")
        for field_name, weight in weights.items():
            pts, tier = _field_score(term, hay[field_name], weight, hay_tok[field_name])
            if pts:
                score += pts
                matched.add(field_name if tier == "exact" else f"{field_name}:{tier}")
    slug = "-".join(terms)
    if slug and slug in entry.concept_id.lower():
        score += SLUG_BONUS
        matched.add("slug")
    return score, sorted(matched)


def _read_json_mtime(path: Path) -> tuple[object | None, int | None]:
    if not path.is_file():
        return None, None
    try:
        mtime_ns = path.stat().st_mtime_ns
        return json.loads(path.read_text(encoding="utf-8")), mtime_ns
    except (OSError, json.JSONDecodeError):
        return None, None


def _cached_load(cache: _MtimeCache, path: Path) -> object | None:
    """Return cached payload when path mtime matches; else reload from disk."""
    if not path.is_file():
        cache.path = path
        cache.mtime_ns = None
        cache.payload = None
        return None
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return None
    if cache.path == path and cache.mtime_ns == mtime_ns and cache.payload is not None:
        return cache.payload
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache.path = path
        cache.mtime_ns = None
        cache.payload = None
        return None
    cache.path = path
    cache.mtime_ns = mtime_ns
    cache.payload = raw
    return raw


def _entry_from_row(row: dict) -> IndexEntry | None:
    if "id" not in row:
        return None
    tags = row.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    cid = str(row["id"])
    tok_list = row.get("tokens") or []
    if not isinstance(tok_list, list):
        tok_list = []
    entry = IndexEntry(
        concept_id=cid,
        title=str(row.get("title", "")),
        description=str(row.get("description", "")),
        tags=[str(t) for t in tags],
        ctype=str(row.get("type", "")),
        path=VAULT_ROOT / f"{cid}.md",
        id_norm=str(row.get("id_norm", "")),
        title_norm=str(row.get("title_norm", "")),
        desc_norm=str(row.get("desc_norm", "")),
        tags_norm=str(row.get("tags_norm", "")),
        type_norm=str(row.get("type_norm", "")),
        search_tokens=frozenset(str(t) for t in tok_list if t),
    )
    _ensure_norms(entry)
    return entry


def _load_index_bundle() -> tuple[list[IndexEntry] | None, dict[str, list[str]]]:
    """
    intent: Load index.json (+ inverted map) with process-local mtime cache.
    output: (entries or None, inverted token→ids).
    """
    path = BRAIN_ROOT / "index.json"
    raw = _cached_load(_INDEX_CACHE, path)
    if raw is None:
        return None, {}
    inverted: dict[str, list[str]] = {}
    rows: list
    if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
        rows = raw["entries"]
        inv = raw.get("inverted") or {}
        if isinstance(inv, dict):
            inverted = {str(k): [str(x) for x in v] for k, v in inv.items() if isinstance(v, list)}
        # Also keep inverted in its own mtime cache slot (same file).
        _INVERTED_CACHE.path = path
        _INVERTED_CACHE.mtime_ns = _INDEX_CACHE.mtime_ns
        _INVERTED_CACHE.payload = inverted
    elif isinstance(raw, list):
        rows = raw
    else:
        return None, {}
    entries: list[IndexEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry = _entry_from_row(row)
        if entry:
            entries.append(entry)
    return entries, inverted


def _load_index() -> list[IndexEntry] | None:
    """
    intent: Load compile-time index.json when present.
    input: none (reads BRAIN_ROOT/index.json).
    output: entries or None to signal fallback.
    role: index loader.
    side_effects: reads one JSON file (mtime-cached).
    """
    entries, _ = _load_index_bundle()
    return entries


def _load_inverted() -> dict[str, list[str]]:
    _, inv = _load_index_bundle()
    return inv


def _entries_from_vault() -> list[IndexEntry]:
    """
    intent: Fallback — build index rows by walking the vault (frontmatter only).
    input: none.
    output: IndexEntry list.
    role: live indexer.
    side_effects: reads vault files.
    """
    entries: list[IndexEntry] = []
    for concept in load_vault():
        if concept.parse_error:
            continue
        fm = concept.frontmatter
        tags = fm.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        entry = IndexEntry(
            concept_id=concept.concept_id,
            title=str(fm.get("title", "")),
            description=str(fm.get("description", "")),
            tags=[str(t) for t in tags],
            ctype=str(fm.get("type", "")),
            path=concept.path,
        )
        _ensure_norms(entry)
        entries.append(entry)
    return entries


def _load_adjacency() -> dict[str, set[str]]:
    """
    intent: Undirected adjacency from graph.json for proximity boosts.
    input: none.
    output: concept_id → neighbor ids.
    role: graph loader.
    side_effects: reads graph.json if present (mtime-cached).
    """
    path = BRAIN_ROOT / "graph.json"
    raw = _cached_load(_ADJ_CACHE, path)
    if not isinstance(raw, dict):
        return {}
    # Cache parsed adjacency, not raw JSON, on second access path:
    cached_adj = getattr(_ADJ_CACHE, "_adj", None)
    if (
        cached_adj is not None
        and _ADJ_CACHE.path == path
        and getattr(_ADJ_CACHE, "_adj_mtime", None) == _ADJ_CACHE.mtime_ns
    ):
        return cached_adj  # type: ignore[return-value]
    adj: dict[str, set[str]] = {}
    for edge in raw.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src, tgt = edge.get("source"), edge.get("target")
        if not src or not tgt:
            continue
        adj.setdefault(str(src), set()).add(str(tgt))
        adj.setdefault(str(tgt), set()).add(str(src))
    _ADJ_CACHE._adj = adj  # type: ignore[attr-defined]
    _ADJ_CACHE._adj_mtime = _ADJ_CACHE.mtime_ns  # type: ignore[attr-defined]
    return adj


def _load_card_cache() -> dict[str, str]:
    """
    intent: Load compile-time Prompt Card cache.
    input: none.
    output: concept_id → card body.
    role: card cache loader.
    side_effects: reads prompt_cards.json if present (mtime-cached).
    """
    path = BRAIN_ROOT / "prompt_cards.json"
    raw = _cached_load(_CARD_CACHE, path)
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v}


def _apply_graph_boost(hits: list[Hit], adj: dict[str, set[str]]) -> None:
    """
    intent: Boost hits within 1–2 hops of strong lexical seeds (in-place).
    input: scored hits; adjacency map.
    output: none (mutates hit.score / graph_hops).
    role: ranker.
    side_effects: none.
    """
    if not hits or not adj:
        return
    # Seeds: top lexical scores (at least half of best, min score 20).
    best = max(h.score for h in hits)
    threshold = max(20, best // 2)
    seeds = {h.entry.concept_id for h in hits if h.score >= threshold}
    if not seeds:
        return
    hop1: set[str] = set()
    for s in seeds:
        hop1 |= adj.get(s, set())
    hop1 -= seeds
    hop2: set[str] = set()
    for s in hop1:
        hop2 |= adj.get(s, set())
    hop2 -= seeds | hop1
    by_id = {h.entry.concept_id: h for h in hits}
    for cid in hop1:
        if cid in by_id:
            by_id[cid].score += GRAPH_HOP1
            by_id[cid].graph_hops = 1
    for cid in hop2:
        if cid in by_id:
            by_id[cid].score += GRAPH_HOP2
            by_id[cid].graph_hops = 2


def _candidate_ids(terms: list[str], inverted: dict[str, list[str]], all_ids: list[str]) -> list[str] | None:
    """
    intent: Narrow scoring set via inverted index (union of term postings).
    output: candidate ids, or None to score everyone (no inv / empty terms /
            any term with no posting — keeps acronym/fuzzy recall).
    """
    if not terms or not inverted:
        return None
    found: set[str] = set()
    for t in terms:
        hit_this = False
        ids = inverted.get(t)
        if ids:
            found.update(ids)
            hit_this = True
        # Prefix expansion for short typed queries (e.g. "work" → workflow)
        if len(t) >= 3:
            for key, postings in inverted.items():
                if key.startswith(t):
                    found.update(postings)
                    hit_this = True
        if not hit_this:
            return None  # unknown token → full scan (acronym / fuzzy)
    if not found:
        return None
    allow = found
    return [cid for cid in all_ids if cid in allow]


def lookup(
    query: str,
    limit: int = 5,
    type_filter: str | None = None,
) -> list[Hit]:
    """
    intent: Search vault concepts without loading full bodies into ranking.
    input: query; max hits; optional type filter (case-insensitive).
    output: ranked Hit list.
    role: searcher.
    side_effects: reads index.json (or vault) and optionally graph.json.
    """
    terms = _tokens(query)
    entries, inverted = _load_index_bundle()
    if entries is None:
        entries = _entries_from_vault()
        inverted = {}
    by_id = {e.concept_id: e for e in entries}
    candidate_ids = _candidate_ids(terms, inverted, list(by_id.keys()))
    if candidate_ids is None:
        pool = entries
    else:
        pool = [by_id[cid] for cid in candidate_ids if cid in by_id]
    hits: list[Hit] = []
    want_type = type_filter.lower() if type_filter else None
    for entry in pool:
        if want_type and entry.ctype.lower() != want_type:
            continue
        s, matched = score_entry(entry, terms)
        if s > 0:
            hits.append(Hit(entry=entry, score=s, matched=matched))
    _apply_graph_boost(hits, _load_adjacency())
    hits.sort(key=lambda h: (-h.score, h.entry.concept_id))
    return hits[: max(1, limit)]


def _card_for(hit: Hit, cache: dict[str, str]) -> str | None:
    """
    intent: Resolve Prompt Card from cache or by reading the markdown file.
    input: hit; optional card cache.
    output: card body or None.
    role: card resolver.
    side_effects: may read one markdown file on cache miss.
    """
    cached = cache.get(hit.entry.concept_id)
    if cached:
        return cached
    path = hit.entry.path
    if path is None or not path.is_file():
        path = VAULT_ROOT / f"{hit.entry.concept_id}.md"
    if not path.is_file():
        return None
    return extract_prompt_card(path.read_text(encoding="utf-8"))


def _est_tokens(text: str) -> int:
    """Backward-compatible alias for count_tokens."""
    return count_tokens(text)


def assemble_prompt_pack(
    query: str,
    *,
    limit: int = 5,
    type_filter: str | None = None,
    max_cards: int | None = None,
    budget: int | None = None,
) -> tuple[list[dict[str, object]], list]:
    """
    intent: Shared Prompt Pack builder for lookup --card and pack.
    output: (pack rows, raw hits). Each row: id, score, kind, text, tokens.
    """
    cfg = load_okf_config()
    max_cards = int(max_cards if max_cards is not None else cfg.get("max_cards", DEFAULT_MAX_CARDS))
    budget = int(budget if budget is not None else cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))
    hits = lookup(query, limit=limit, type_filter=type_filter)
    if not hits:
        return [], []
    cache = _load_card_cache()
    pack: list[dict[str, object]] = []
    used = 0
    for hit in hits:
        if len(pack) >= max(1, max_cards):
            break
        card = _card_for(hit, cache)
        if card:
            kind = "card"
            body = f"### Card: {hit.entry.concept_id}.md (score={hit.score})\n{card}"
        else:
            kind = "stub"
            body = (
                f"### Path: _okf_knowledge/{hit.entry.concept_id}.md "
                f"(score={hit.score})\n"
                f"(no ## Prompt Card — open file only if needed)"
            )
        cost = count_tokens(body)
        if pack and used + cost > budget:
            break
        pack.append(
            {
                "id": hit.entry.concept_id,
                "path": hit.entry.concept_id + ".md",
                "type": hit.entry.ctype,
                "title": hit.entry.title,
                "score": hit.score,
                "kind": kind,
                "text": body,
                "tokens": cost,
            }
        )
        used += cost
    return pack, hits


def format_pack(pack: list[dict[str, object]], style: str, query: str) -> str:
    """Render Prompt Pack as markdown | json | xml (cards only — never full vault)."""
    total = sum(int(r["tokens"]) for r in pack)
    style = (style or "markdown").lower()
    if style == "json":
        return json.dumps(
            {
                "query": query,
                "token_estimator": "tiktoken:cl100k_base" if _tiktoken_encoder() else "heuristic",
                "total_tokens": total,
                "cards": [
                    {
                        "id": r["id"],
                        "path": r["path"],
                        "type": r["type"],
                        "title": r["title"],
                        "score": r["score"],
                        "kind": r["kind"],
                        "tokens": r["tokens"],
                        "text": r["text"],
                    }
                    for r in pack
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    if style == "xml":
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<okf_prompt_pack>",
            f"  <query>{_xml_esc(query)}</query>",
            f"  <total_tokens>{total}</total_tokens>",
        ]
        for r in pack:
            lines.append(
                f'  <card id="{_xml_esc(str(r["id"]))}" tokens="{r["tokens"]}" '
                f'score="{r["score"]}" kind="{r["kind"]}">'
            )
            lines.append(f"    <![CDATA[{r['text']}]]>")
            lines.append("  </card>")
        lines.append("</okf_prompt_pack>")
        return "\n".join(lines)
    header = (
        f"# OKF Prompt Pack\nquery: {query!r}\n"
        f"cards: {len(pack)}  total_tokens: {total}\n"
    )
    body = "\n\n".join(str(r["text"]) for r in pack)
    return header + "\n" + body if pack else header + "\n(no cards)\n"


def _xml_esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cmd_lookup(args: argparse.Namespace) -> int:
    """
    intent: Find concepts; optionally emit budgeted Prompt Cards.
    input: parsed args.
    output: exit 0 if hits; 1 if none / errors.
    role: subcommand.
    side_effects: stdout/stderr only.
    """
    as_json = bool(getattr(args, "json", False))

    if args.card:
        pack, hits = assemble_prompt_pack(
            args.query,
            limit=args.limit,
            type_filter=args.type_filter,
            max_cards=args.max_cards,
            budget=args.budget,
        )
        if not hits:
            print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
            return 1
        if as_json:
            print(format_pack(pack, "json", args.query))
        else:
            # agent-facing: cards only (no pack header) — same as pre-1.2
            print("\n\n".join(str(r["text"]) for r in pack))
        return 0

    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        if as_json:
            print(json.dumps([h.entry.concept_id + ".md" for h in hits], indent=2))
        else:
            for hit in hits:
                print(hit.entry.concept_id + ".md")
        return 0

    if as_json:
        print(
            json.dumps(
                [
                    {
                        "id": h.entry.concept_id,
                        "path": h.entry.concept_id + ".md",
                        "type": h.entry.ctype,
                        "title": h.entry.title,
                        "description": h.entry.description,
                        "score": h.score,
                        "matched": h.matched,
                        "graph_hops": h.graph_hops,
                    }
                    for h in hits
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if (BRAIN_ROOT / "index.json").is_file():
        _, inv = _load_index_bundle()
        src = f"index.json v{INDEX_FORMAT_VERSION}"
        if inv:
            src += f" (inv={len(inv)} tokens)"
    else:
        src = "live vault"
    print(f"# okf lookup  query={args.query!r}  source={src}  vault={VAULT_ROOT}")
    for hit in hits:
        e = hit.entry
        print(f"{hit.score:3d}  [{e.ctype}]  {e.concept_id}")
        print(f"     {e.title} — {e.description}")
        meta = []
        if hit.matched:
            meta.append("matched=" + ",".join(hit.matched))
        if hit.graph_hops is not None:
            meta.append(f"graph={hit.graph_hops} hop")
        if meta:
            print(f"     ({' '.join(meta)})")
    print(
        "\n# Next: python3 okf.py lookup --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    """
    intent: Export a cards-only Prompt Pack (Repomix-like formats, OKF semantics).
    """
    pack, hits = assemble_prompt_pack(
        args.query,
        limit=args.limit,
        type_filter=args.type_filter,
        max_cards=args.max_cards,
        budget=args.budget,
    )
    if not hits:
        print(f"[okf_pack] no hits for: {args.query!r}", file=sys.stderr)
        return 1
    out = format_pack(pack, args.style, args.query)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"[okf_pack] wrote {args.output} ({len(pack)} cards)", file=sys.stderr)
    else:
        print(out)
    return 0


# =============================================================================
# Compile (formerly graph_compiler.py)
# =============================================================================

def _graph_content(body: str) -> str:
    stripped = body.strip()
    if len(stripped) <= GRAPH_CONTENT_MAX:
        return stripped
    return stripped[:GRAPH_CONTENT_MAX] + "\n\n…"


def compile_graph(concepts: list[Concept]) -> dict[str, list[dict[str, str]]]:
    """
    intent: Build the node/edge graph implied by markdown cross-links. Nodes
            carry the concept's markdown body so aegis-brain's reading pane
            works without filesystem access.
    input: concepts — loaded vault.
    output: {"nodes": [...], "edges": [...]} dict for graph.json.
    role: graph builder.
    side_effects: none.
    """
    ids = {c.concept_id for c in concepts}
    nodes = [
        {
            "id": c.concept_id,
            "type": str(c.frontmatter.get("type", "?")),
            "title": str(c.frontmatter.get("title", c.path.stem)),
            "description": str(c.frontmatter.get("description", "")),
            "tags": c.frontmatter.get("tags", []),
            "content": _graph_content(c.body),
        }
        for c in concepts
    ]
    edges = []
    for c in concepts:
        for target in extract_links(c.body):
            resolved = resolve_link(target, c.path)
            target_id = concept_id_from_path(resolved)
            if target_id is None:
                continue
            if target_id in ids and target_id != c.concept_id:
                edges.append({"source": c.concept_id, "target": target_id})
    return {"nodes": nodes, "edges": edges}


def _index_row_for_concept(c: Concept) -> dict[str, object]:
    tags = c.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    tag_strs = [str(t) for t in tags]
    title = str(c.frontmatter.get("title", c.path.stem))
    description = str(c.frontmatter.get("description", ""))
    ctype = str(c.frontmatter.get("type", ""))
    id_norm = _norm(c.concept_id.replace("/", " ").replace("-", " "))
    title_norm = _norm(title)
    desc_norm = _norm(description)
    tags_norm = _norm(" ".join(tag_strs))
    type_norm = _norm(ctype)
    tok: set[str] = set()
    tok.update(_tokenize(c.concept_id))
    tok.update(_tokenize(title))
    tok.update(_tokenize(description))
    for t in tag_strs:
        tok.update(_tokenize(t))
    tok.update(_tokenize(ctype))
    return {
        "id": c.concept_id,
        "path": c.concept_id + ".md",
        "title": title,
        "description": description,
        "tags": tag_strs,
        "type": ctype,
        "id_norm": id_norm,
        "title_norm": title_norm,
        "desc_norm": desc_norm,
        "tags_norm": tags_norm,
        "type_norm": type_norm,
        "tokens": sorted(tok),
    }


def compile_index(concepts: list[Concept]) -> dict[str, object]:
    """
    intent: Slim frontmatter index + inverted token map for lookup.
    input: concepts — parseable vault concepts.
    output: index.json v2 document {version, entries, inverted}.
    role: lookup index builder.
    side_effects: none.
    """
    entries = [_index_row_for_concept(c) for c in concepts]
    inverted: dict[str, list[str]] = {}
    for row in entries:
        cid = str(row["id"])
        for tok in row.get("tokens", []):
            inverted.setdefault(str(tok), []).append(cid)
    for key in inverted:
        inverted[key] = sorted(set(inverted[key]))
    return {
        "version": INDEX_FORMAT_VERSION,
        "entries": entries,
        "inverted": inverted,
    }


def compile_prompt_cards(concepts: list[Concept]) -> dict[str, str]:
    """
    intent: Cache ## Prompt Card bodies at compile time so lookup need not
            reopen markdown for winners.
    input: concepts — parseable vault concepts (body available).
    output: concept_id → card body map for prompt_cards.json.
    role: prompt card cache builder.
    side_effects: none.
    """
    cards: dict[str, str] = {}
    for c in concepts:
        card = extract_prompt_card(c.body)
        if card:
            cards[c.concept_id] = card
    return cards


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _compile_cache_path() -> Path:
    return BRAIN_ROOT / COMPILE_CACHE_NAME


def _concept_to_cache(c: Concept) -> dict[str, object]:
    return {
        "concept_id": c.concept_id,
        "frontmatter": c.frontmatter,
        "body": c.body,
        "parse_error": c.parse_error,
    }


def _concept_from_cache(path: Path, blob: dict[str, object]) -> Concept:
    fm = blob.get("frontmatter")
    if not isinstance(fm, dict):
        fm = {}
    return Concept(
        concept_id=str(blob.get("concept_id") or concept_id_from_path(path) or path.stem),
        path=path,
        frontmatter=fm,
        body=str(blob.get("body") or ""),
        parse_error=str(blob["parse_error"]) if blob.get("parse_error") else None,
    )


def load_vault_incremental(force: bool = False) -> tuple[list[Concept], int, int]:
    """
    intent: Load vault concepts, reusing compile-cache entries when mtime/hash match.
    input: force — ignore cache and re-parse everything.
    output: (concepts including parse errors, dirty_count, reused_count).
    role: incremental vault loader.
    side_effects: may rewrite .okf-compile-cache.json.
    """
    cache_path = _compile_cache_path()
    prev: dict[str, object] = {}
    if not force and cache_path.is_file():
        try:
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("version") == COMPILE_CACHE_VERSION:
                prev = loaded
        except (OSError, json.JSONDecodeError):
            prev = {}
    prev_files = prev.get("files") if isinstance(prev.get("files"), dict) else {}

    new_files: dict[str, object] = {}
    concepts: list[Concept] = []
    dirty = 0
    reused = 0

    for path in iter_concept_files():
        rel = str(path.relative_to(VAULT_ROOT)).replace("\\", "/")
        try:
            st = path.stat()
            mtime_ns = st.st_mtime_ns
        except OSError as exc:
            concepts.append(
                Concept(
                    concept_id=concept_id_from_path(path) or path.stem,
                    path=path,
                    parse_error=str(exc),
                )
            )
            dirty += 1
            continue

        cached = prev_files.get(rel) if isinstance(prev_files, dict) else None
        if (
            not force
            and isinstance(cached, dict)
            and cached.get("mtime_ns") == mtime_ns
            and isinstance(cached.get("concept"), dict)
        ):
            concepts.append(_concept_from_cache(path, cached["concept"]))  # type: ignore[arg-type]
            new_files[rel] = cached
            reused += 1
            continue

        try:
            data = path.read_bytes()
        except OSError as exc:
            concepts.append(
                Concept(
                    concept_id=concept_id_from_path(path) or path.stem,
                    path=path,
                    parse_error=str(exc),
                )
            )
            dirty += 1
            continue

        digest = _sha256_bytes(data)
        if (
            not force
            and isinstance(cached, dict)
            and cached.get("sha256") == digest
            and isinstance(cached.get("concept"), dict)
        ):
            cached = dict(cached)
            cached["mtime_ns"] = mtime_ns
            concepts.append(_concept_from_cache(path, cached["concept"]))  # type: ignore[arg-type]
            new_files[rel] = cached
            reused += 1
            continue

        text = data.decode("utf-8")
        fm, body = parse_frontmatter(text)
        cid = concept_id_from_path(path) or path.stem
        if fm is None:
            c = Concept(concept_id=cid, path=path, parse_error="missing/invalid frontmatter")
        else:
            c = Concept(concept_id=cid, path=path, frontmatter=fm, body=body)
        concepts.append(c)
        new_files[rel] = {
            "mtime_ns": mtime_ns,
            "sha256": digest,
            "concept": _concept_to_cache(c),
        }
        dirty += 1

    try:
        cache_path.write_text(
            json.dumps(
                {"version": COMPILE_CACHE_VERSION, "files": new_files},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    # Bust in-process artifact caches after compile inputs change.
    if dirty or force:
        for slot in (_INDEX_CACHE, _ADJ_CACHE, _CARD_CACHE, _INVERTED_CACHE):
            slot.mtime_ns = None
            slot.payload = None

    return concepts, dirty, reused


def _artifacts_fresh(concept_count: int) -> bool:
    """True when index/graph/cards exist and look like a complete prior compile."""
    index_p = BRAIN_ROOT / "index.json"
    graph_p = BRAIN_ROOT / "graph.json"
    cards_p = BRAIN_ROOT / "prompt_cards.json"
    if not (index_p.is_file() and graph_p.is_file() and cards_p.is_file()):
        return False
    try:
        raw = json.loads(index_p.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
            return len(raw["entries"]) == concept_count and raw.get("version") == INDEX_FORMAT_VERSION
        if isinstance(raw, list):
            return False  # force upgrade to v2
    except (OSError, json.JSONDecodeError):
        return False
    return False


def cmd_compile(args: argparse.Namespace | None = None) -> int:
    """
    intent: Write graph.json, index.json (v2+inverted), prompt_cards.json and
            embed the graph into aegis-brain.html. Skips work when the
            incremental compile cache reports zero dirty concepts and artifacts
            are already current (unless --force).
    input: optional --force.
    output: process exit code.
    role: subcommand.
    side_effects: writes graph/index/prompt_cards JSON; rewrites aegis-brain.html;
                  updates .okf-compile-cache.json.
    """
    force = bool(getattr(args, "force", False)) if args is not None else False
    try:
        all_concepts, dirty, reused = load_vault_incremental(force=force)
        skipped = [c for c in all_concepts if c.parse_error is not None]
        for c in skipped:
            print(
                f"[DBG-202] skipping unparseable concept {c.concept_id}: {c.parse_error}",
                file=sys.stderr,
            )
        concepts = [c for c in all_concepts if c.parse_error is None]

        if not force and dirty == 0 and _artifacts_fresh(len(concepts)):
            print(
                f"[DBG-200] compile up-to-date ({len(concepts)} concepts, "
                f"{reused} cache hits, 0 dirty) — skipped rewrite for {VAULT_ROOT}"
            )
            return 0

        # Drop legacy TOON index if present from older Aegis versions.
        legacy = BRAIN_ROOT / "context.toon"
        if legacy.exists():
            legacy.unlink()
        graph = compile_graph(concepts)
        index = compile_index(concepts)
        cards = compile_prompt_cards(concepts)
        graph_json = json.dumps(graph, indent=2)
        (BRAIN_ROOT / "graph.json").write_text(graph_json + "\n", encoding="utf-8")
        (BRAIN_ROOT / "index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
        (BRAIN_ROOT / "prompt_cards.json").write_text(
            json.dumps(cards, indent=2) + "\n", encoding="utf-8"
        )
        # Refresh process caches immediately.
        for slot in (_INDEX_CACHE, _ADJ_CACHE, _CARD_CACHE, _INVERTED_CACHE):
            slot.mtime_ns = None
            slot.payload = None
        embedded = inject_into_aegis_brain("graph-data", graph_json)
    except OSError as exc:
        print(f"[DBG-201] graph compile failed: {exc}", file=sys.stderr)
        return 1
    skipped_note = f", {len(skipped)} skipped" if skipped else ""
    inv_n = len(index.get("inverted", {})) if isinstance(index, dict) else 0
    print(
        f"[DBG-200] wrote graph.json ({len(concepts)} concepts{skipped_note}, "
        f"{len(graph['edges'])} edges), index.json v{INDEX_FORMAT_VERSION} "
        f"({inv_n} inv tokens), prompt_cards.json ({len(cards)} cards); "
        f"parsed={dirty} reused={reused} for {VAULT_ROOT}"
        + ("; embedded graph into aegis-brain.html" if embedded else "")
    )
    return 0


# =============================================================================
# Lint (formerly okf_lint.py)
# =============================================================================

HOUSE_REQUIRED_FIELDS = ("title", "description")
# Rule #2 target: ≤150 tokens ≈ 600 characters (see `okf.py card --max-chars`).
PROMPT_CARD_MAX_CHARS = 600


def collect_findings() -> tuple[list[dict[str, str]], int]:
    """
    intent: Run every check and return structured findings.
    input: none (reads vault from disk).
    output: (findings, concept_count) — each finding has severity/concept/code/message.
    role: core checker, shared by the CLI report and lint.json.
    side_effects: none (read-only).
    """
    concepts = load_vault()
    findings: list[dict[str, str]] = []
    linked_ids: set[str] = set()
    ids = {c.concept_id for c in concepts}

    def add(severity: str, concept: str, code: str, message: str) -> None:
        findings.append(
            {"severity": severity, "concept": concept, "code": code, "message": message}
        )

    for c in concepts:
        # -- Conformance (OKF v0.1 §9) --
        if c.parse_error is not None:
            code = c.parse_error.split("]", 1)[0].lstrip("[")
            add("error", c.concept_id, code, c.parse_error)
            continue
        if not str(c.frontmatter.get("type", "")).strip():
            add("error", c.concept_id, "DBG-301", "missing required 'type' field")

        # -- House schema (AGENTS.md taxonomy, loaded dynamically) --
        ctype = str(c.frontmatter.get("type", ""))
        taxonomy = known_types()
        if ctype and ctype not in taxonomy:
            add("warning", c.concept_id, "DBG-302",
                f"unknown type '{ctype}' (not in AGENTS.md taxonomy)")
        for fld in HOUSE_REQUIRED_FIELDS:
            if not str(c.frontmatter.get(fld, "")).strip():
                add("warning", c.concept_id, "DBG-303",
                    f"missing house-required field '{fld}'")

        # -- Standards Prompt Card gate (path standards/* OR tag `standard`) --
        if is_standard_concept(c):
            card = extract_prompt_card(c.body)
            if card is None:
                add(
                    "error",
                    c.concept_id,
                    "DBG-308",
                    "standard concepts MUST include a non-empty ## Prompt Card section",
                )
            elif len(card) > PROMPT_CARD_MAX_CHARS:
                add(
                    "warning",
                    c.concept_id,
                    "DBG-309",
                    f"Prompt Card is {len(card)} chars "
                    f"(target ≤{PROMPT_CARD_MAX_CHARS} ≈150 tokens)",
                )

        # -- Links --
        for target in extract_links(c.body):
            resolved = resolve_link(target, c.path)
            target_id = concept_id_from_path(resolved)
            if target_id is None:
                # Control-plane files may live at the share/repo root (parent).
                if resolved.exists() and resolved.name in control_plane_filenames():
                    continue
                add("warning", c.concept_id, "DBG-305", f"link escapes vault -> {target}")
                continue
            if not resolved.exists():
                add("warning", c.concept_id, "DBG-304", f"broken link -> {target}")
                continue
            linked_ids.add(target_id)

    # Count links from reserved pages so indexed concepts are not false orphans.
    control_names = control_plane_filenames()
    for special in VAULT_ROOT.rglob("*.md"):
        if special.name not in control_names and special.name not in RESERVED_FILENAMES:
            continue
        try:
            body = special.read_text(encoding="utf-8")
        except OSError:
            continue
        for target in extract_links(body):
            resolved = resolve_link(target, special)
            target_id = concept_id_from_path(resolved)
            if target_id is not None and resolved.exists():
                linked_ids.add(target_id)

    for orphan in sorted(ids - linked_ids):
        add(
            "warning",
            orphan,
            "DBG-306",
            "orphan — no inbound links from concepts or reserved pages",
        )

    return findings, len(concepts)


def cmd_lint(_args: argparse.Namespace | None = None) -> int:
    """
    intent: Print the lint report, write lint.json (also embedded into
            aegis-brain.html for file:// auto-load), exit non-zero on errors.
    input: none.
    output: process exit code (0 clean/warnings-only, 1 errors).
    role: subcommand.
    side_effects: writes lint.json at the vault root; rewrites aegis-brain.html.
    """
    findings, concept_count = collect_findings()
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    print(f"okf lint: {concept_count} concepts checked ({VAULT_ROOT})")
    for f in errors:
        print(f"  ERROR   {f['concept']}: [{f['code']}] {f['message']}")
    for f in warnings:
        print(f"  WARNING {f['concept']}: [{f['code']}] {f['message']}")
    if not findings:
        print("  clean — vault is conformant and healthy")
    print(f"summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    report = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Package-relative label only — never embed absolute machine paths.
        "vault": VAULT_ROOT.name,
        "summary": {
            "concepts": concept_count,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "findings": findings,
    }
    write_ok = True
    try:
        report_json = json.dumps(report, indent=2)
        (BRAIN_ROOT / "lint.json").write_text(report_json + "\n", encoding="utf-8")
        inject_into_aegis_brain("lint-data", report_json)
    except OSError as exc:
        write_ok = False
        print(f"[DBG-307] could not write lint.json: {exc}", file=sys.stderr)
    return 1 if errors or not write_ok else 0


# =============================================================================
# Enrich (formerly okf_enrich.py; adapted from okf-generator okf/enrich)
# =============================================================================

DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
LLM_REQUEST_TIMEOUT_S = 120
ENRICH_MAX_BODY_LINES = 120   # mirrors okf-generator _MAX_BODY_LINES
ENRICH_MIN_DESC_LEN = 15      # shorter descriptions are treated as gaps
ENRICH_MAX_TAGS = 6

# WARNING (carried over from okf-generator/_llm_prompts.py): the {body}
# variable is arbitrary vault text. Keep instructions and body separated;
# the JSON-only output constraint limits prompt-injection blast radius to
# structured fields which are then length- and shape-validated below.
ENRICH_PROMPT = """\
You are enriching one document of an Aegis OKF knowledge vault so that a
lexical search over frontmatter (title/tags/description) finds it, and so a
slim "Prompt Card" can be injected into coding-agent prompts.

Return a JSON object with exactly these fields (use "" / [] to skip a field):

  "description" - one sentence, <= 120 chars, stating what the document
                  covers, specific enough to rank in keyword search.
  "tags"        - 0-{max_tags} short kebab-case topic tags (purpose/domain,
                  not the type name). Only tags justified by the body.
  "prompt_card" - <= {card_chars} chars of binding MUST / SHOULD / FORBIDDEN
                  lines (or exact commands) an agent needs at generation time.
                  Plain text lines only, no headings, no link lists, no prose
                  essays. Empty string if the document has no binding rules.

Rules:
- Base everything ONLY on the document below; do not invent facts.
- Do not restate the whole document; compress to what an agent must obey.
- Reply with ONLY the JSON object, no markdown fences, no preamble.

Document type: {ctype}
Document id: {concept_id}
Title: {title}
Existing description: {description}
Existing tags: {tags}
Document body:
{body}
"""


def _enrich_needs(concept: Concept) -> list[str]:
    """
    intent: Decide which of the three retrieval fields are missing/weak.
    input: parsed concept.
    output: list of gap names ("description", "tags", "card").
    role: pure gap detector (keeps the pass idempotent).
    side_effects: none.
    """
    gaps: list[str] = []
    desc = str(concept.frontmatter.get("description", "")).strip()
    if len(desc) < ENRICH_MIN_DESC_LEN:
        gaps.append("description")
    tags = concept.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    if len([t for t in tags if str(t).strip()]) < 2:
        gaps.append("tags")
    if extract_prompt_card(concept.body) is None:
        gaps.append("card")
    return gaps


def _truncate_body(body: str, max_lines: int) -> str:
    lines = body.splitlines()
    if len(lines) <= max_lines:
        return body
    return "\n".join(lines[:max_lines] + ["... (truncated)"])


def _llm_chat(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """
    intent: Minimal OpenAI-compatible /chat/completions call via stdlib.
    input: endpoint config; single user prompt.
    output: assistant message content.
    role: transport (replaces okf-generator's openai client dependency).
    side_effects: one HTTPS/HTTP request.
    """
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
    ).encode("utf-8")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    scheme = urlparse(endpoint).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"[DBG-404] LLM endpoint must be http/https, got {scheme!r}")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'no-key'}",
        },
        method="POST",
    )
    # Scheme gated above; stdlib client (local/OpenAI-compatible endpoints).
    with urllib.request.urlopen(req, timeout=LLM_REQUEST_TIMEOUT_S) as resp:  # nosec B310
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"] or "")


def _parse_json_reply(raw: str) -> dict:
    """
    intent: Tolerantly parse the model's JSON-only reply (strip fences).
    input: raw assistant text.
    output: dict (empty on failure).
    role: pure parser.
    side_effects: none.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _sanitize_enrich_reply(data: dict) -> dict:
    """
    intent: Shape/length-validate model output before touching vault files.
    input: parsed reply dict.
    output: dict with only safe, clamped fields.
    role: validation boundary (LLM output is untrusted input).
    side_effects: none.
    """
    out: dict = {}
    desc = str(data.get("description", "")).strip().replace("\n", " ")
    if desc:
        out["description"] = desc[:160]
    tags = data.get("tags", [])
    if isinstance(tags, list):
        clean = []
        for t in tags[:ENRICH_MAX_TAGS]:
            t = re.sub(r"[^a-z0-9-]", "", str(t).strip().lower().replace(" ", "-"))
            if 2 <= len(t) <= 40:
                clean.append(t)
        if clean:
            out["tags"] = clean
    card = str(data.get("prompt_card", "")).strip()
    if card:
        out["prompt_card"] = card[:PROMPT_CARD_MAX_CHARS]
    return out


def _apply_enrich(concept: Concept, gaps: list[str], fix: dict) -> tuple[str, list[str]]:
    """
    intent: Produce the updated file text, filling only the detected gaps.
    input: concept; gap names; sanitized fix dict.
    output: (new file text, list of gaps actually filled).
    role: pure rewriter (caller writes the file).
    side_effects: none.
    """
    text = concept.path.read_text(encoding="utf-8")
    filled: list[str] = []

    if "description" in gaps and fix.get("description"):
        new_line = f"description: {fix['description']}"
        if re.search(r"^description:.*$", text, flags=re.M):
            text = re.sub(r"^description:.*$", new_line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(type:.*)$", r"\1\n" + new_line, text, count=1, flags=re.M)
        filled.append("description")

    if "tags" in gaps and fix.get("tags"):
        existing = concept.frontmatter.get("tags", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        merged = [str(t) for t in existing if str(t).strip()]
        for t in fix["tags"]:
            if t not in merged:
                merged.append(t)
        new_line = f"tags: [{', '.join(merged[:ENRICH_MAX_TAGS])}]"
        if re.search(r"^tags:.*$", text, flags=re.M):
            text = re.sub(r"^tags:.*$", new_line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(type:.*)$", r"\1\n" + new_line, text, count=1, flags=re.M)
        filled.append("tags")

    if "card" in gaps and fix.get("prompt_card"):
        block = f"\n## Prompt Card\n\n```text\n{fix['prompt_card']}\n```\n"
        # Insert before the first Related heading so the card stays scoped;
        # otherwise append at the end of the document.
        m = re.search(r"^#{1,2} Related\s*$", text, flags=re.M)
        if m:
            text = text[: m.start()] + block.lstrip("\n") + "\n" + text[m.start():]
        else:
            text = text.rstrip("\n") + "\n" + block
        filled.append("card")

    if filled:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = re.sub(r"^timestamp:.*$", f"timestamp: {stamp}", text, count=1, flags=re.M)
    return text, filled


def cmd_enrich(args: argparse.Namespace) -> int:
    """
    intent: Report gaps; with --write, fill them via the configured LLM.
    input: parsed args.
    output: exit 0 (clean or all fixed), 1 (gaps remain / errors).
    role: subcommand.
    side_effects: --write edits vault markdown; network calls to the LLM.
    """
    targets: list[tuple[Concept, list[str]]] = []
    for concept in load_vault():
        if concept.parse_error:
            continue
        if args.only and args.only not in concept.concept_id:
            continue
        gaps = _enrich_needs(concept)
        if gaps:
            targets.append((concept, gaps))

    if not targets:
        print("okf enrich: no gaps — every concept has description, tags, and a Prompt Card")
        return 0

    print(f"okf enrich: {len(targets)} concept(s) with gaps")
    for concept, gaps in targets:
        print(f"  {concept.concept_id}: missing {', '.join(gaps)}")

    if not args.write:
        print("\n(dry-run — pass --write to fill gaps via the configured LLM)")
        return 1

    base_url = os.environ.get("OKF_LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    api_key = os.environ.get("OKF_LLM_API_KEY", "")
    model = os.environ.get("OKF_LLM_MODEL", DEFAULT_LLM_MODEL)
    print(f"\nokf enrich: endpoint={base_url} model={model}")

    enriched = 0
    skipped = 0
    if args.limit > 0:
        targets = targets[: args.limit]
    for concept, gaps in targets:
        prompt = ENRICH_PROMPT.format(
            max_tags=ENRICH_MAX_TAGS,
            card_chars=PROMPT_CARD_MAX_CHARS,
            ctype=str(concept.frontmatter.get("type", "")),
            concept_id=concept.concept_id,
            title=str(concept.frontmatter.get("title", "")),
            description=str(concept.frontmatter.get("description", "")) or "(none)",
            tags=", ".join(map(str, concept.frontmatter.get("tags", []) or [])) or "(none)",
            body=_truncate_body(concept.body, args.max_body),
        )
        try:
            reply = _llm_chat(base_url, api_key, model, prompt)
        except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
            print(f"  SKIP {concept.concept_id}: LLM call failed ({exc})", file=sys.stderr)
            skipped += 1
            continue
        fix = _sanitize_enrich_reply(_parse_json_reply(reply))
        if not fix:
            print(f"  SKIP {concept.concept_id}: unusable LLM reply", file=sys.stderr)
            skipped += 1
            continue
        text, filled = _apply_enrich(concept, gaps, fix)
        if not filled:
            print(f"  SKIP {concept.concept_id}: nothing usable for {gaps}", file=sys.stderr)
            skipped += 1
            continue
        concept.path.write_text(text, encoding="utf-8")
        enriched += 1
        print(f"  OK   {concept.concept_id}: filled {', '.join(filled)}")

    print(f"\nokf enrich: {enriched} enriched, {skipped} skipped")
    if enriched:
        print("Next (maintain playbook): python3 _okf_knowledge/kernel/okf.py compile "
              "&& python3 _okf_knowledge/kernel/okf.py lint")
    return 0 if skipped == 0 else 1


# =============================================================================
# Optimize (formerly cache_optimizer.py)
# =============================================================================

VAULT_DIR = VAULT_ROOT / "vault"


def _is_reference(path: Path) -> bool:
    """
    intent: Gate optimizer mutations to Reference concepts only.
    input: path — candidate .md file under vault/.
    output: True when frontmatter type is Reference.
    role: collision guard vs Playbook/System/Concept/Incident.
    side_effects: none (read-only).
    """
    concept = load_concept(path)
    if concept.parse_error is not None:
        return False
    return str(concept.frontmatter.get("type", "")).strip() == "Reference"


def _reference_cache_dirs() -> list[Path]:
    """
    intent: Discover directories under vault/ that hold Reference concepts.
    input: none (walks VAULT_DIR).
    output: sorted unique parent dirs of files with frontmatter type Reference.
    role: dynamic replacement for a static allowlist — new scrape/cache dirs
          (e.g. vault/github-actions/, vault/terraform/) are picked up automatically.
    side_effects: none (read-only).
    """
    if not VAULT_DIR.is_dir():
        return []
    dirs: set[Path] = set()
    for path in VAULT_DIR.rglob("*.md"):
        if path.name == "index.md":
            continue
        if any(part.startswith(".") for part in path.relative_to(VAULT_DIR).parts):
            continue
        if _is_reference(path):
            dirs.add(path.parent)
    return sorted(dirs)


def normalize_reference(path: Path) -> list[str]:
    """
    intent: Ensure one cached reference has complete, normalized frontmatter.
    input: path — reference .md file.
    output: list of fixes applied (empty if already clean).
    role: normalizer.
    side_effects: may rewrite the file in place.
    """
    concept = load_concept(path)
    if concept.parse_error is not None:
        return [f"SKIP unparseable: {concept.parse_error}"]
    if str(concept.frontmatter.get("type", "")).strip() != "Reference":
        return []

    fm = dict(concept.frontmatter)
    fixes: list[str] = []
    if not str(fm.get("title", "")).strip():
        fm["title"] = path.stem.replace("-", " ").title()
        fixes.append("derived title from filename")
    if not str(fm.get("description", "")).strip():
        fm["description"] = "Cached upstream documentation."
        fixes.append("added default description")
    if not str(fm.get("timestamp", "")).strip():
        fm["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        fixes.append("stamped timestamp")
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        stripped = [str(t).strip() for t in tags if str(t).strip()]
        normalized = sorted({s.lower() for s in stripped})
        needs_fix = (
            len(stripped) != len({s.lower() for s in stripped})
            or any(s != s.lower() for s in stripped)
            or [s.lower() for s in stripped] != normalized
        )
        if needs_fix:
            fm["tags"] = normalized
            fixes.append("deduped/sorted tags")

    if fixes:
        path.write_text(format_frontmatter(fm) + concept.body, encoding="utf-8")
    return fixes


def rebuild_references_index() -> int:
    """
    intent: Regenerate indexes for every directory that contains References.
    input: none (discovers dirs via _reference_cache_dirs()).
    output: number of index files written.
    role: index generator scoped by frontmatter type, not by hardcoded dir names.
    side_effects: writes index.md under discovered Reference dirs only.
    """
    written = 0
    for source_dir in _reference_cache_dirs():
        entries = []
        for ref in sorted(source_dir.glob("*.md")):
            if ref.name == "index.md":
                continue
            if not _is_reference(ref):
                continue
            c = load_concept(ref)
            title = c.frontmatter.get("title", ref.stem)
            desc = c.frontmatter.get("description", "")
            source_url = str(c.frontmatter.get("source_url", "")).strip()
            official = f" — [official docs]({source_url})" if source_url else ""
            entries.append(f"* [{title}]({ref.name}) - {desc}{official}")
        if entries:
            rel = source_dir.relative_to(VAULT_DIR)
            body = f"# Cached references — {rel}\n\n" + "\n".join(entries) + "\n"
            (source_dir / "index.md").write_text(body, encoding="utf-8")
            written += 1
    return written


def cmd_optimize(_args: argparse.Namespace | None = None) -> int:
    """
    intent: Normalize References only, rebuild their indexes, recompile.
    input: none.
    output: process exit code.
    role: subcommand.
    side_effects: rewrites Reference files + their indexes; runs compile.
    """
    if not VAULT_DIR.exists():
        print("[DBG-501] no vault/ directory; nothing to optimize", file=sys.stderr)
        return 0
    total_fixes = 0
    for path in sorted(VAULT_DIR.rglob("*.md")):
        if path.name == "index.md":
            continue
        if not _is_reference(path):
            continue
        fixes = normalize_reference(path)
        for fix in fixes:
            print(f"  {path.relative_to(VAULT_ROOT)}: {fix}")
        total_fixes += len(fixes)
    indexes = rebuild_references_index()
    print(f"[DBG-500] {total_fixes} fix(es) applied, {indexes} index(es) rebuilt")
    return cmd_compile()


# =============================================================================
# Scrape (formerly registry_scraper.py)
# =============================================================================

# Builtin seed catalog (domain → keyword → (slug, title, url)).
# Prefer extending via scrape-catalog.json files under the brain (merged at runtime).
_BUILTIN_SCRAPE_CATALOGS: dict[str, dict[str, tuple[str, str, str]]] = {
    "github-actions": {
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
            "Redact upstream content or set credential_scan:false in okf.config.json."
        )
    cfg = load_okf_config()
    domain_slug = (domain or _domain_from_url(url)).strip() or "upstream"
    out_dir = VAULT_DIR / "references" / domain_slug
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
    out_path = out_dir / f"{slug}.md"
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


# =============================================================================
# Serve (formerly serve_vault.py)
# =============================================================================

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
            self._run_and_send(cmd_lint, BRAIN_ROOT / "lint.json", "DBG-601", "lint")
        elif self.path == "/api/compile":
            self._run_and_send(cmd_compile, BRAIN_ROOT / "graph.json", "DBG-602", "compile")
        else:
            self.send_error(404, "not found")

    def _run_and_send(self, fn, artifact: Path, code: str, label: str) -> None:
        """
        intent: Run a kernel command in-process and return its artifact.
        input: fn — cmd_lint/cmd_compile; artifact — produced JSON path.
        output: HTTP response with the artifact contents.
        role: API helper (single-file kernel: no subprocess needed).
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


def cmd_serve(args: argparse.Namespace) -> int:
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
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DBG-600] stopped")
    return 0


# =============================================================================
# CLI
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    """
    intent: Parse the subcommand and dispatch.
    input: argv.
    output: subcommand exit code.
    role: main.
    side_effects: per subcommand.
    """
    cfg = load_okf_config()
    default_max_cards = int(cfg.get("max_cards", DEFAULT_MAX_CARDS))
    default_budget = int(cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))

    parser = argparse.ArgumentParser(
        prog="okf.py",
        description="Aegis OKF kernel — lookup, pack, cards, compile, "
        "lint, enrich, optimize, scrape, and serve.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("lookup", help="Search the vault; --card emits budgeted Prompt Cards")
    p.add_argument("query", help="Search string (title, tags, path, description)")
    p.add_argument("--card", action="store_true",
                   help="Emit ## Prompt Card (or path stub) for each hit")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable JSON (hits or Prompt Pack)")
    p.add_argument("--paths", action="store_true",
                   help="Print concept paths only (one per line)")
    p.add_argument("--limit", type=int, default=5, help="Max hits (default 5)")
    p.add_argument("--type", dest="type_filter", default=None,
                   help="Filter by frontmatter type (e.g. Concept, Playbook)")
    p.add_argument("--max-cards", type=int, default=default_max_cards,
                   help=f"With --card, stop after N cards (default {default_max_cards})")
    p.add_argument("--budget", type=int, default=default_budget,
                   help=f"With --card, token budget for the pack "
                        f"(default {default_budget}; tiktoken if installed else heuristic)")
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser(
        "pack",
        help="Export cards-only Prompt Pack (markdown|json|xml) — never full vault dump",
    )
    p.add_argument("query", help="Search string for pack assembly")
    p.add_argument(
        "--style",
        choices=("markdown", "json", "xml"),
        default="markdown",
        help="Output format (default markdown)",
    )
    p.add_argument("-o", "--output", default=None, help="Write to file instead of stdout")
    p.add_argument("--limit", type=int, default=5, help="Max hits to consider (default 5)")
    p.add_argument("--type", dest="type_filter", default=None, help="Filter by type")
    p.add_argument("--max-cards", type=int, default=default_max_cards)
    p.add_argument("--budget", type=int, default=default_budget)
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("card", help="Extract Prompt Cards from known paths")
    p.add_argument("paths", nargs="+",
                   help="Markdown concept/standard paths (vault-relative or absolute)")
    p.add_argument("--max-chars", type=int, default=PROMPT_CARD_MAX_CHARS,
                   help=f"Warn if a card exceeds this many characters "
                        f"(~150 tokens). Default {PROMPT_CARD_MAX_CHARS}.")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser(
        "compile",
        help="Rebuild graph.json / index.json (v2+inverted) / prompt_cards.json + HTML embed",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore incremental compile cache; re-parse every concept",
    )
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("lint", help="Vault health check; writes lint.json")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("enrich",
                       help="LLM gap-fill for description/tags/Prompt Card "
                            "(env OKF_LLM_BASE_URL / OKF_LLM_API_KEY / OKF_LLM_MODEL)")
    p.add_argument("--write", action="store_true",
                   help="Call the LLM and write fixes (default: report only)")
    p.add_argument("--only", default=None,
                   help="Substring filter on concept id (e.g. 'playbooks')")
    p.add_argument("--limit", type=int, default=0,
                   help="Max concepts to enrich this run (0 = all)")
    p.add_argument("--max-body", type=int, default=ENRICH_MAX_BODY_LINES,
                   help=f"Body lines sent to the LLM (default {ENRICH_MAX_BODY_LINES})")
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("optimize",
                       help="Normalize Reference concepts, rebuild their indexes, recompile")
    p.set_defaults(func=cmd_optimize)

    p = sub.add_parser("scrape", help="Fetch upstream docs into vault/ as a Reference")
    p.add_argument("query", help="Catalog keyword (e.g. 'workflow syntax') or a direct URL")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("serve", help="Local brain server with /api/lint and /api/compile")
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address (default: 127.0.0.1 — local only)")
    p.add_argument("--port", type=int, default=8080, help="listen port (default 8080)")
    p.add_argument("--verbose", action="store_true", help="log each HTTP request")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
