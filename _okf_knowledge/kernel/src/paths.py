"""OKF kernel paths and shared constants."""
from __future__ import annotations

import os
import re
from pathlib import Path

# Scripts live in kernel/src/; brain root is parent of kernel/ (`_okf_knowledge/`).
KERNEL_SRC = Path(__file__).resolve().parent
VAULT_ROOT = Path(
    os.environ.get("OKF_VAULT_ROOT", str(KERNEL_SRC.parent.parent))
).resolve()
BRAIN_ROOT = VAULT_ROOT
# Visualizer template + compiled graph live next to kernel modules.
AEGIS_BRAIN_HTML = KERNEL_SRC / "aegis-brain.html"
GRAPH_JSON = KERNEL_SRC / "graph.json"
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
DEFAULT_MAX_CARDS = 8
DEFAULT_TOKEN_BUDGET = 1200
OKFIGNORE_NAME = ".okfignore"
HOUSE_REQUIRED_FIELDS = ("title", "description")
PROMPT_CARD_MAX_CHARS = 600
CHARS_PER_TOKEN = 4
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
LLM_REQUEST_TIMEOUT_S = 120
ENRICH_MAX_BODY_LINES = 120
ENRICH_MIN_DESC_LEN = 15
ENRICH_MAX_TAGS = 6
