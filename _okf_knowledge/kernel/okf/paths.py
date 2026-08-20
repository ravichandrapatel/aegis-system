"""Shared filesystem paths and tunables.

Naming (PEP 8): module constants are UPPER_SNAKE; locals/params are lower_snake.
Classes elsewhere use CapWords. Do not mix styles in one name (no MaxCards, no okf_X).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Layout:
#   _okf_knowledge/                 ← VAULT_ROOT / BRAIN_ROOT
#     kernel/
#       okf.py                      ← CLI shim
#       okf/                        ← this package (PACKAGE_DIR)
#         assets/
#           brain.html
#           graph.json              ← compile artifact (visualizer + hop-boost)
#     index.json, prompt_cards.json ← compile artifacts at brain root
#     standards/, vault/, …
PACKAGE_DIR = Path(__file__).resolve().parent
VAULT_ROOT = Path(
    os.environ.get("VAULT_ROOT", str(PACKAGE_DIR.parent.parent))
).resolve()
BRAIN_ROOT = VAULT_ROOT
# Directory that holds okf.py + the okf/ package (folder name is kernel/).
TOOLING_DIR = PACKAGE_DIR.parent
CLI_SCRIPT = TOOLING_DIR / "okf.py"

ASSETS_DIR = PACKAGE_DIR / "assets"
BRAIN_HTML = ASSETS_DIR / "brain.html"

GRAPH_JSON = ASSETS_DIR / "graph.json"
INDEX_JSON = BRAIN_ROOT / "index.json"
PROMPT_CARDS_JSON = BRAIN_ROOT / "prompt_cards.json"

RESERVED_FILENAMES = {"index.md", "log.md"}
_CONTROL_PLANE_SEED = {
    "AGENTS.md",
    "README.md",
    "ADR.md",
    "CLAUDE.md",
    "GEMINI.md",
    "COPILOT.md",
    "agent.md",
}
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".cursor",
    ".github",
    ".windsurf",
    ".continue",
    "__pycache__",
    # Tooling tree is not concept markdown.
    "kernel",
    "okf",
}
_TYPE_SEED = {
    "Concept",
    "Playbook",
    "System",
    "Reference",
    "Incident",
}
GRAPH_CONTENT_MAX = 4000
INDEX_FORMAT_VERSION = 2
COMPILE_CACHE_VERSION = 1
COMPILE_CACHE_NAME = ".okf-compile-cache.json"
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]+|\d+")
TITLE_WEIGHT = 10
ID_WEIGHT = 8
TAG_WEIGHT = 6
DESC_WEIGHT = 3
TYPE_WEIGHT = 2
SLUG_BONUS = 12
EXACT_MULT = 3
PREFIX_MULT = 2
SUBSTRING_MULT = 1
GRAPH_HOP1 = 4
GRAPH_HOP2 = 2
MIN_TERM_LEN = 2
TOKEN_BONUS = 4
MIN_PACK_SCORE = 24
FORCE_SCORE = 10_000
DEFAULT_MAX_CARDS = 8
DEFAULT_TOKEN_BUDGET = 1200
DEFAULT_RELATED_LINKS = 3
IGNORE_FILE_NAME = ".okfignore"
HOUSE_REQUIRED_FIELDS = ("title", "description")
STATUS_VALUES = ("draft", "stable", "deprecated")
ACTOR_RE = re.compile(r"^(?:human:\S+|process:\S+|[^/\s]+/[^/\s]+)$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROMPT_CARD_MAX_CHARS = 600
CHARS_PER_TOKEN = 4
