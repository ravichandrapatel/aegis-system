# file_name: okf_common.py
# description: Shared helpers for the Aegis OKF tooling — vault walking,
#              frontmatter parsing, and markdown link extraction. Stdlib only.
# version: 0.4.0
# authors: contributors
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

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
    # _log("[T-01] parsing frontmatter")
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    try:
        end = next(i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---")
    except StopIteration:
        # _log("[T-02] unterminated frontmatter block")
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
    # _log("[T-03] walking vault")
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
        # _log("[T-04] unreadable concept file")
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
    role: shared writer for graph_compiler and okf_lint.
    side_effects: rewrites aegis-brain.html in place.
    """
    # _log("[T-05] injecting payload into aegis-brain.html")
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
        # _log("[T-06] data tag not found in aegis-brain.html")
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


def read_known_types(root: Path = VAULT_ROOT) -> set[str]:
    """
    intent: Parse starter taxonomy from AGENTS.md table or return defaults.
    input: root — vault root.
    output: set of known type strings.
    role: schema reader for lint warnings.
    side_effects: none.
    """
    defaults = {
        "Concept",
        "Playbook",
        "Reference",
        "System",
        "Incident",
        "Module",
        "Vendor",
    }
    agents = root / "AGENTS.md"
    if not agents.is_file():
        agents = root.parent / "AGENTS.md"
    if not agents.is_file():
        return defaults
    found: set[str] = set()
    in_table = False
    for line in agents.read_text(encoding="utf-8").splitlines():
        if "| `type` |" in line or "|--------|" in line:
            in_table = True
            continue
        if in_table and line.startswith("| `"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1].startswith("`") and parts[1].endswith("`"):
                found.add(parts[1].strip("`"))
        elif in_table and line.strip() and not line.startswith("|"):
            break
    return found or defaults
