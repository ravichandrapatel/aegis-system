"""OKF config, ignore rules, token counting, secret scan."""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from src.paths import (
    BRAIN_ROOT,
    CHARS_PER_TOKEN,
    DEFAULT_MAX_CARDS,
    DEFAULT_TOKEN_BUDGET,
    OKFIGNORE_NAME,
    PROMPT_CARD_MAX_CHARS,
    VAULT_ROOT,
)

# Built-in OKF runtime config (formerly okf.config.json).
OKF_CONFIG: dict[str, object] = {
    "max_cards": DEFAULT_MAX_CARDS,
    "token_budget": DEFAULT_TOKEN_BUDGET,
    "prompt_card_max_chars": PROMPT_CARD_MAX_CHARS,
    "reference_max_chars": 20_000,
    "reference_compress": True,
    "credential_scan": True,
    "respect_gitignore": True,
}

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
    (
        re.compile(
            r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[\'\"][^\'\"]{16,}"
        ),
        "credential_assign",
    ),
]


def load_okf_config() -> dict[str, object]:
    """
    intent: Return the built-in OKF runtime config (hardcoded in this module).
    output: shallow copy of OKF_CONFIG.
    """
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    _CONFIG_CACHE = dict(OKF_CONFIG)
    return _CONFIG_CACHE

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

