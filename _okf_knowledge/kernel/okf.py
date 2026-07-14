#!/usr/bin/env python3
# file_name: okf.py
# description: Single-file Aegis OKF kernel — lookup, card, compile, lint,
#              enrich, optimize, scrape, and serve as subcommands. Stdlib only.
#              Consolidates okf_common / prompt_card / okf_lookup /
#              graph_compiler / okf_lint / okf_enrich / cache_optimizer /
#              registry_scraper / serve_vault.
# version: 1.0.0
# authors: contributors
#
# Usage:
#   python3 _okf_knowledge/kernel/okf.py lookup "<query>" [--card] [--paths] ...
#   python3 _okf_knowledge/kernel/okf.py card <path> [<path>...]
#   python3 _okf_knowledge/kernel/okf.py compile
#   python3 _okf_knowledge/kernel/okf.py lint
#   python3 _okf_knowledge/kernel/okf.py enrich [--write] [--only X] [--limit N]
#   python3 _okf_knowledge/kernel/okf.py optimize
#   python3 _okf_knowledge/kernel/okf.py scrape "<query or URL>"
#   python3 _okf_knowledge/kernel/okf.py serve [--port 8080]
"""
intent: One CLI for every kernel operation on the Aegis OKF brain.
input: subcommand + flags (see Usage above); env OKF_VAULT_ROOT overrides the
       brain root; env OKF_LLM_* configures the enrich endpoint.
output: subcommand-specific stdout; compiled artifacts / lint.json / vault
        edits depending on the subcommand.
role: kernel entry point (replaces the previous per-script CLIs).
side_effects: read-only for lookup/card; compile/lint/enrich/optimize/scrape
              write under the brain; serve binds a TCP port.
"""
from __future__ import annotations

import argparse
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
RESERVED_FILENAMES = {"index.md", "log.md"}
IDE_BRIDGE_FILES = {"CLAUDE.md", "GEMINI.md", "COPILOT.md", "agent.md"}
CONTROL_PLANE_FILES = {"AGENTS.md", "README.md", "ADR.md"} | IDE_BRIDGE_FILES
NON_CONCEPT_FILES = RESERVED_FILENAMES | CONTROL_PLANE_FILES
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".cursor",
    ".github",
    ".windsurf",
    ".continue",
}
GRAPH_CONTENT_MAX = 4000

# Matches markdown links, capturing the target: [text](target)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


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
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        parts = rel.parts

        # Skip hidden directories
        if any(p.startswith(".") for p in parts):
            continue

        # Skip base kernel directory but allow modules and vendors subdirectories
        # Handles both root/kernel and root/knowledge/kernel
        if "kernel" in parts:
            idx = parts.index("kernel")
            if len(parts) <= idx + 1 or parts[idx + 1] not in ("modules", "vendors"):
                continue

        # Skip other reserved directories
        if "_inbox" in parts:
            continue

        if any(part in SKIP_DIRS for part in parts):
            continue
        if path.name in NON_CONCEPT_FILES:
            continue
        files.append(path)
    return files


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
        if name in CONTROL_PLANE_FILES:
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
# Rough chars≈tokens*4 for budget enforcement without a tokenizer.
CHARS_PER_TOKEN = 4


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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(query: str) -> list[str]:
    return [
        t
        for t in re.split(r"[^a-z0-9_+.-]+", _norm(query))
        if len(t) >= MIN_TERM_LEN
    ]


def _field_score(term: str, hay: str, weight: int) -> tuple[int, str | None]:
    """
    intent: Score one term against one haystack with exact/prefix/substring tiers.
    input: term; normalized haystack; base field weight.
    output: (points, match tier name) or (0, None).
    role: pure scorer helper.
    side_effects: none.
    """
    if not hay or not term:
        return 0, None
    tokens = hay.split()
    if term == hay or term in tokens:
        return weight * EXACT_MULT, "exact"
    if any(tok.startswith(term) for tok in tokens) or hay.startswith(term):
        return weight * PREFIX_MULT, "prefix"
    if term in hay:
        return weight * SUBSTRING_MULT, "substr"
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
    tag_s = " ".join(entry.tags)
    hay = {
        "id": _norm(entry.concept_id.replace("/", " ").replace("-", " ")),
        "title": _norm(entry.title),
        "desc": _norm(entry.description),
        "tags": _norm(tag_s),
        "type": _norm(entry.ctype),
    }
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
        for field_name, weight in weights.items():
            pts, tier = _field_score(term, hay[field_name], weight)
            if pts:
                score += pts
                matched.add(field_name if tier == "exact" else f"{field_name}:{tier}")
    slug = "-".join(terms)
    if slug and slug in entry.concept_id.lower():
        score += SLUG_BONUS
        matched.add("slug")
    return score, sorted(matched)


def _load_index() -> list[IndexEntry] | None:
    """
    intent: Load compile-time index.json when present.
    input: none (reads BRAIN_ROOT/index.json).
    output: entries or None to signal fallback.
    role: index loader.
    side_effects: reads one JSON file.
    """
    path = BRAIN_ROOT / "index.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, list):
        return None
    entries: list[IndexEntry] = []
    for row in raw:
        if not isinstance(row, dict) or "id" not in row:
            continue
        tags = row.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        cid = str(row["id"])
        entries.append(
            IndexEntry(
                concept_id=cid,
                title=str(row.get("title", "")),
                description=str(row.get("description", "")),
                tags=[str(t) for t in tags],
                ctype=str(row.get("type", "")),
                path=VAULT_ROOT / f"{cid}.md",
            )
        )
    return entries


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
        entries.append(
            IndexEntry(
                concept_id=concept.concept_id,
                title=str(fm.get("title", "")),
                description=str(fm.get("description", "")),
                tags=[str(t) for t in tags],
                ctype=str(fm.get("type", "")),
                path=concept.path,
            )
        )
    return entries


def _load_adjacency() -> dict[str, set[str]]:
    """
    intent: Undirected adjacency from graph.json for proximity boosts.
    input: none.
    output: concept_id → neighbor ids.
    role: graph loader.
    side_effects: reads graph.json if present.
    """
    path = BRAIN_ROOT / "graph.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    adj: dict[str, set[str]] = {}
    for edge in raw.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src, tgt = edge.get("source"), edge.get("target")
        if not src or not tgt:
            continue
        adj.setdefault(str(src), set()).add(str(tgt))
        adj.setdefault(str(tgt), set()).add(str(src))
    return adj


def _load_card_cache() -> dict[str, str]:
    """
    intent: Load compile-time Prompt Card cache.
    input: none.
    output: concept_id → card body.
    role: card cache loader.
    side_effects: reads prompt_cards.json if present.
    """
    path = BRAIN_ROOT / "prompt_cards.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
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
    entries = _load_index()
    if entries is None:
        entries = _entries_from_vault()
    hits: list[Hit] = []
    want_type = type_filter.lower() if type_filter else None
    for entry in entries:
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
    return max(1, len(text) // CHARS_PER_TOKEN) if text else 0


def cmd_lookup(args: argparse.Namespace) -> int:
    """
    intent: Find concepts; optionally emit budgeted Prompt Cards.
    input: parsed args.
    output: exit 0 if hits; 1 if none / errors.
    role: subcommand.
    side_effects: stdout/stderr only.
    """
    hits = lookup(args.query, limit=args.limit, type_filter=args.type_filter)
    if not hits:
        print(f"[okf_lookup] no hits for: {args.query!r}", file=sys.stderr)
        return 1

    if args.paths:
        for hit in hits:
            print(hit.entry.concept_id + ".md")
        return 0

    if args.card:
        cache = _load_card_cache()
        chunks: list[str] = []
        used_tokens = 0
        for hit in hits:
            if len(chunks) >= max(1, args.max_cards):
                break
            card = _card_for(hit, cache)
            if card:
                piece = (
                    f"### Card: {hit.entry.concept_id}.md (score={hit.score})\n{card}"
                )
            else:
                # Never dead-end: a path stub keeps the agent moving in one shot.
                piece = (
                    f"### Path: _okf_knowledge/{hit.entry.concept_id}.md "
                    f"(score={hit.score})\n"
                    f"(no ## Prompt Card — open file only if needed)"
                )
            cost = _est_tokens(piece)
            if chunks and used_tokens + cost > args.budget:
                break
            chunks.append(piece)
            used_tokens += cost
        print("\n\n".join(chunks))
        return 0

    # default listing (tiny — safe to show agents as a menu)
    src = "index.json" if (BRAIN_ROOT / "index.json").is_file() else "live vault"
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
            print(f"     ({'; '.join(meta)})")
    print(
        "\n# Next: python3 okf.py lookup --card "
        f"{args.query!r}   # inject Prompt Cards only"
    )
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


def compile_index(concepts: list[Concept]) -> list[dict[str, object]]:
    """
    intent: Slim frontmatter index for lookup (no bodies — cheap retrieval).
    input: concepts — parseable vault concepts.
    output: list of index entries for index.json.
    role: lookup index builder.
    side_effects: none.
    """
    entries: list[dict[str, object]] = []
    for c in concepts:
        tags = c.frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        entries.append(
            {
                "id": c.concept_id,
                "path": c.concept_id + ".md",
                "title": str(c.frontmatter.get("title", c.path.stem)),
                "description": str(c.frontmatter.get("description", "")),
                "tags": [str(t) for t in tags],
                "type": str(c.frontmatter.get("type", "")),
            }
        )
    return entries


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


def cmd_compile(_args: argparse.Namespace | None = None) -> int:
    """
    intent: Write graph.json, index.json, prompt_cards.json and embed the
            graph into aegis-brain.html for file:// auto-load.
    input: none (reads vault from disk).
    output: process exit code.
    role: subcommand.
    side_effects: writes graph/index/prompt_cards JSON; rewrites aegis-brain.html.
    """
    try:
        all_concepts = load_vault()
        skipped = [c for c in all_concepts if c.parse_error is not None]
        for c in skipped:
            print(
                f"[DBG-202] skipping unparseable concept {c.concept_id}: {c.parse_error}",
                file=sys.stderr,
            )
        concepts = [c for c in all_concepts if c.parse_error is None]
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
        embedded = inject_into_aegis_brain("graph-data", graph_json)
    except OSError as exc:
        print(f"[DBG-201] graph compile failed: {exc}", file=sys.stderr)
        return 1
    skipped_note = f", {len(skipped)} skipped" if skipped else ""
    print(
        f"[DBG-200] wrote graph.json ({len(concepts)} concepts{skipped_note}, "
        f"{len(graph['edges'])} edges), index.json, prompt_cards.json "
        f"({len(cards)} cards) for {VAULT_ROOT}"
        + ("; embedded graph into aegis-brain.html" if embedded else "")
    )
    return 0


# =============================================================================
# Lint (formerly okf_lint.py)
# =============================================================================

# Taxonomy from AGENTS.md — drift is a warning, not an error (OKF tolerates unknown types).
# Vault taxonomy (Zone 4) + kernel execution types (Zone 2). Keep them distinct
# so vendor/module docs do not collide with passive vault Concepts/Systems.
KNOWN_TYPES = {
    "Concept",
    "Playbook",
    "System",
    "Reference",
    "Incident",
    "Module",
    "Vendor",
}
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

        # -- House schema (AGENTS.md) --
        ctype = str(c.frontmatter.get("type", ""))
        if ctype and ctype not in KNOWN_TYPES:
            add("warning", c.concept_id, "DBG-302",
                f"unknown type '{ctype}' (not in AGENTS.md taxonomy)")
        for fld in HOUSE_REQUIRED_FIELDS:
            if not str(c.frontmatter.get(fld, "")).strip():
                add("warning", c.concept_id, "DBG-303",
                    f"missing house-required field '{fld}'")

        # -- Standards Prompt Card gate (ADR follow-up #3 / Rule #2) --
        # Binding house law under standards/* MUST expose a non-empty ## Prompt Card.
        if c.concept_id.startswith("standards/"):
            card = extract_prompt_card(c.body)
            if card is None:
                add(
                    "error",
                    c.concept_id,
                    "DBG-308",
                    "standards/* MUST include a non-empty ## Prompt Card section",
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
                if resolved.exists() and resolved.name in CONTROL_PLANE_FILES:
                    continue
                add("warning", c.concept_id, "DBG-305", f"link escapes vault -> {target}")
                continue
            if not resolved.exists():
                add("warning", c.concept_id, "DBG-304", f"broken link -> {target}")
                continue
            linked_ids.add(target_id)

    # Count links from reserved pages so indexed concepts are not false orphans.
    for special in VAULT_ROOT.rglob("*.md"):
        if special.name not in NON_CONCEPT_FILES:
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
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'no-key'}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=LLM_REQUEST_TIMEOUT_S) as resp:
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
# Cached upstream dumps land here (or in domain cache dirs that only hold References).
REFERENCE_CACHE_DIRS = {"references", "github-actions"}


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
    intent: Regenerate indexes only for Reference cache directories.
    input: none (reads vault/ tree).
    output: number of index files written.
    role: index generator scoped to avoid colliding with Playbook/System indexes.
    side_effects: writes index.md under Reference cache dirs only.
    """
    if not VAULT_DIR.is_dir():
        return 0
    written = 0
    for source_dir in sorted(p for p in VAULT_DIR.iterdir() if p.is_dir()):
        if source_dir.name not in REFERENCE_CACHE_DIRS:
            continue
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
            body = f"# Cached references — {source_dir.name}\n\n" + "\n".join(entries) + "\n"
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
        "description": "Cached upstream documentation, fetched by `okf.py scrape`.",
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


def cmd_scrape(args: argparse.Namespace) -> int:
    """
    intent: Resolve query, fetch, write back, remind about optimize.
    input: parsed args (query string).
    output: process exit code.
    role: subcommand.
    side_effects: network fetch + vault write.
    """
    slug, title, url = resolve_query(args.query)
    try:
        content = fetch_page(url)
    except (URLError, OSError, TimeoutError) as exc:
        print(f"[DBG-402] upstream fetch failed for {url}: {exc}", file=sys.stderr)
        return 1
    out_path = write_reference(slug, title, url, content)
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
    parser = argparse.ArgumentParser(
        prog="okf.py",
        description="Aegis OKF kernel — one CLI for lookup, cards, compile, "
        "lint, enrich, optimize, scrape, and serve.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("lookup", help="Search the vault; --card emits budgeted Prompt Cards")
    p.add_argument("query", help="Search string (title, tags, path, description)")
    p.add_argument("--card", action="store_true",
                   help="Emit ## Prompt Card (or path stub) for each hit")
    p.add_argument("--paths", action="store_true",
                   help="Print concept paths only (one per line)")
    p.add_argument("--limit", type=int, default=5, help="Max hits (default 5)")
    p.add_argument("--type", dest="type_filter", default=None,
                   help="Filter by frontmatter type (e.g. Concept, Playbook)")
    p.add_argument("--max-cards", type=int, default=DEFAULT_MAX_CARDS,
                   help=f"With --card, stop after N cards (default {DEFAULT_MAX_CARDS})")
    p.add_argument("--budget", type=int, default=DEFAULT_TOKEN_BUDGET,
                   help=f"With --card, approx token budget for the pack "
                        f"(default {DEFAULT_TOKEN_BUDGET}; chars//{CHARS_PER_TOKEN})")
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser("card", help="Extract Prompt Cards from known paths")
    p.add_argument("paths", nargs="+",
                   help="Markdown concept/standard paths (vault-relative or absolute)")
    p.add_argument("--max-chars", type=int, default=PROMPT_CARD_MAX_CHARS,
                   help=f"Warn if a card exceeds this many characters "
                        f"(~150 tokens). Default {PROMPT_CARD_MAX_CHARS}.")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser("compile",
                       help="Rebuild graph.json / index.json / prompt_cards.json + HTML embed")
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
