"""Vault load/parse/link helpers."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from src.models import Concept
from src.config import path_ignored
from src.paths import (
    AEGIS_BRAIN_HTML,
    RESERVED_FILENAMES,
    SKIP_DIRS,
    VAULT_ROOT,
    _CONTROL_PLANE_SEED,
    _LINK_RE,
    _TYPE_SEED,
)


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
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        parts = rel.parts

        # Skip hidden directories
        if any(p.startswith(".") for p in parts):
            continue

        # Skip kernel/ (Python tools only — not concept markdown)
        if "kernel" in parts:
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
    output: set of type names (includes Concept, Playbook, …).
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

def inject_into_aegis_brain(
    tag_id: str,
    payload_json: str,
    html_path: Path | None = None,
) -> bool:
    """
    intent: Embed a JSON payload into aegis-brain.html's data script tag so the
            graph auto-loads even when the file is opened as file://.
    input: tag_id — "graph-data" or "lint-data"; payload_json — serialized JSON;
           html_path — defaults to kernel/src/aegis-brain.html.
    output: True if the tag was found and replaced, False otherwise.
    role: shared writer for compile and lint.
    side_effects: rewrites aegis-brain.html in place.
    """
    path = html_path if html_path is not None else AEGIS_BRAIN_HTML
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8")
    # Escape "</" so the payload cannot terminate the <script> tag early.
    safe = payload_json.replace("</", "<\\/")
    pattern = re.compile(
        rf'(<script\b[^>]*\bid="{tag_id}"[^>]*>).*?(</script>)',
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
    path.write_text(new_html, encoding="utf-8")
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

