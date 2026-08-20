"""Vault load/parse/link helpers."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from okf.models import Concept
from okf.config import path_ignored
from okf.paths import (
    BRAIN_HTML,
    RESERVED_FILENAMES,
    SKIP_DIRS,
    VAULT_ROOT,
    _CONTROL_PLANE_SEED,
    _LINK_RE,
    _TYPE_SEED,
)


_UNSUPPORTED_VALUE_RE = re.compile(r"^[|>&*]")
_INLINE_COMMENT_RE = re.compile(r"\s+#.*$")

try:  # Optional, like tiktoken: present → full OKF frontmatter.
    import yaml as _yaml
except ImportError:  # pragma: no cover - environment dependent
    _yaml = None  # type: ignore[assignment]


def yaml_available() -> bool:
    """True when PyYAML is importable, so nested-map frontmatter parses."""
    return _yaml is not None


def _strip_inline_comment(value: str) -> str:
    """Drop a YAML ` # comment` tail from an unquoted scalar."""
    if value[:1] in ("'", '"'):
        return value
    return _INLINE_COMMENT_RE.sub("", value).strip()


def _jsonify(value: object) -> object:
    """
    intent: Coerce a YAML-loaded value into something json.dumps can write.
    input: any value from yaml.safe_load.
    output: str / int / float / bool / None / list / dict of the same.
    role: normalizer.
    side_effects: none.

    PyYAML resolves `at: 2026-06-20T22:53:05Z` to a datetime and `2026-09-23`
    to a date. Both would raise in the compile cache and index writers, so
    dates become ISO strings here — the form they were written in.
    """
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """Return (frontmatter block, body) or None when there is no `---` fence."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    try:
        end = next(i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---")
    except StopIteration:
        return None
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


def parse_frontmatter(text: str) -> tuple[dict[str, object] | None, str]:
    """
    intent: Split a markdown document into (frontmatter dict, body).
    input: text — full file contents.
    output: (dict, body), or (None, text) when the block is absent or unparseable.
    role: pure parser.
    side_effects: none.

    PyYAML is used when importable, because OKF expresses its provenance,
    trust, and computation families as nested maps (`generated: {by, at}`,
    `sources: [{id, resource}]`). The hand-rolled subset below cannot represent
    those, so without PyYAML a conformant OKF bundle is rejected outright —
    which §4.1 forbids of a consumer. `okf.py capabilities` reports which path
    is active.
    """
    split = _split_frontmatter(text)
    if split is None:
        return None, text
    block, body = split
    if _yaml is not None:
        try:
            loaded = _yaml.safe_load(block) if block.strip() else {}
        except _yaml.YAMLError:
            return None, text
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            return None, text
        return {str(k): _jsonify(v) for k, v in loaded.items()}, body
    return _parse_frontmatter_subset(text)


def _parse_frontmatter_subset(text: str) -> tuple[dict[str, object] | None, str]:
    """
    intent: PyYAML-free fallback covering flat `key: value`, inline `key: [a, b]`,
            and block lists.
    input: text — full file contents.
    output: (dict or None if unsupported, body string).
    role: pure parser.
    side_effects: none.

    A deliberate subset. Constructs it cannot represent — block scalars
    (`|`, `>`), nested maps, anchors and aliases — return None so lint reports
    DBG-002 loudly, instead of silently storing a mangled value that would then
    be indexed and injected into agent prompts. All scalars are strings.
    """
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    try:
        end = next(i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---")
    except StopIteration:
        return None, text

    fm: dict[str, object] = {}
    i = 1
    while i < end:
        raw = lines[i]
        line = raw.strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if ":" not in line:
            return None, text
        if raw[:1] in (" ", "\t"):
            # Indented `key: value` here means a nested map, which this parser
            # cannot represent. Block list items are consumed below, not here.
            return None, text
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if _UNSUPPORTED_VALUE_RE.match(value):
            return None, text
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            fm[key] = [v for v in items if v]
            i += 1
            continue
        if value == "":
            items: list[str] = []
            j = i + 1
            while j < end:
                m = re.match(r"^(\s*)-\s+(.*)$", lines[j])
                if not m:
                    break
                items.append(_strip_inline_comment(m.group(2).strip()).strip("'\""))
                j += 1
            if items:
                fm[key] = items
                i = j
                continue
            fm[key] = ""
            i += 1
            continue
        fm[key] = _strip_inline_comment(value).strip("'\"")
        i += 1
    body = "\n".join(lines[end + 1 :])
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
    input: none — reads the house schema standard, then falls back to the seed.
    output: set of type names (includes Concept, Playbook, …).
    role: lint taxonomy source.
    side_effects: none (read-only).

    Previously this scraped any `| \\`Backticked\\` |` table row out of AGENTS.md,
    so editing an unrelated table there silently changed lint behaviour. The
    schema standard is the documented source of truth, so read that instead.
    """
    types = set(_TYPE_SEED)
    schema = VAULT_ROOT / "standards" / "okf-house-schema.md"
    if not schema.is_file():
        return types
    try:
        text = schema.read_text(encoding="utf-8")
    except OSError:
        return types
    # The `type:` line of the required-frontmatter example enumerates the taxonomy:
    #   type: Concept          # Concept | Playbook | System | Reference | Incident
    match = re.search(r"^type:.*?#(.*)$", text, re.MULTILINE)
    if match:
        for name in re.findall(r"[A-Z][A-Za-z0-9_-]*", match.group(1)):
            types.add(name)
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
    intent: Render a frontmatter block that the reader will accept back.
    input: fm — frontmatter dict, possibly containing OKF nested families
           (`generated`, `sources`, `executor`).
    output: --- delimited YAML block ending with newline.
    role: shared writer for reference tooling.
    side_effects: none.

    PyYAML does the dumping when present, because it is the only way to
    guarantee the output parses back: hand-rolled quoting is what let
    `pack_force_when: [@workspace]` ship as invalid YAML. The flat fallback
    keeps working for producers running without PyYAML, which can only emit
    flat frontmatter anyway.
    """
    if _yaml is not None:
        dumped = _yaml.safe_dump(
            fm,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        return f"---\n{dumped}---\n"
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {escape_yaml_scalar(str(v))}")
        elif isinstance(value, list):
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

def inject_into_brain(
    tag_id: str,
    payload_json: str,
    html_path: Path | None = None,
) -> bool:
    """
    intent: Embed a JSON payload into assets/brain.html's data script tag so the
            graph auto-loads even when the file is opened as file://.
    input: tag_id — "graph-data" or "lint-data"; payload_json — serialized JSON;
           html_path — defaults to okf/assets/brain.html.
    output: True if the tag was found and replaced, False otherwise.
    role: shared writer for compile and lint.
    side_effects: rewrites assets/brain.html in place.
    """
    path = html_path if html_path is not None else BRAIN_HTML
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
            f"[DBG-203] okf-brain.html missing <script id=\"{tag_id}\"> block",
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

