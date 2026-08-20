# file_name: tokens.py
# description: CLI to count tokens for files and directories (no model call).
# version: 1.0.0
# authors: contributors
"""Token usage report for paths — reuses config.count_tokens."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from okf.config import _tiktoken_encoder, count_tokens

# Default text-ish extensions when walking directories (skip binaries by default).
_DEFAULT_EXTS = frozenset(
    {
        ".md",
        ".mdc",
        ".txt",
        ".py",
        ".pyi",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
        ".bash",
        ".zsh",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".rb",
        ".php",
        ".css",
        ".scss",
        ".html",
        ".xml",
        ".svg",
        ".sql",
        ".tf",
        ".hcl",
        ".dockerfile",
        ".env.example",
        ".gitignore",
        ".okfignore",
        ".csv",
        ".tsv",
        ".rst",
        ".adoc",
    }
)

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".cursor",
    }
)


def token_method() -> str:
    """
    intent: Label the active token counter.
    output: 'tiktoken:cl100k_base' or 'heuristic'.
    """
    enc = _tiktoken_encoder()
    if enc is not None:
        return "tiktoken:cl100k_base"
    return "heuristic"


def _ext_ok(path: Path, exts: frozenset[str] | None) -> bool:
    if exts is None:
        return True
    suf = path.suffix.lower()
    if suf in exts:
        return True
    # extensionless names like Dockerfile, Makefile
    name = path.name.lower()
    return name in exts or f".{name}" in exts


def _collect_files(
    roots: list[Path],
    *,
    recursive: bool,
    exts: frozenset[str] | None,
) -> list[Path]:
    """
    intent: Expand file/dir roots into a sorted unique file list.
    input: paths; whether to recurse; optional extension allow-list (None = all).
    output: resolved file Paths.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    def add_file(p: Path) -> None:
        try:
            rp = p.resolve()
        except OSError:
            return
        if rp in seen or not rp.is_file():
            return
        if not _ext_ok(rp, exts):
            return
        seen.add(rp)
        found.append(rp)

    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            # Explicit file paths always count (even if extension filtered).
            try:
                rp = root.resolve()
            except OSError:
                continue
            if rp not in seen and rp.is_file():
                seen.add(rp)
                found.append(rp)
            continue
        if not root.is_dir():
            continue
        if recursive:
            for dirpath, dirnames, filenames in root.walk(top_down=True):
                # Skip known junk only — keep .github / .cursor when passed as roots
                # or when not in _SKIP_DIR_NAMES.
                dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
                for name in filenames:
                    add_file(dirpath / name)
        else:
            for child in sorted(root.iterdir()):
                if child.is_file():
                    add_file(child)

    found.sort(key=lambda p: p.as_posix())
    return found


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    except OSError:
        return None


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()


def count_paths(
    paths: list[str],
    *,
    recursive: bool = True,
    all_files: bool = False,
    extensions: list[str] | None = None,
) -> dict[str, object]:
    """
    intent: Build a token usage report for files and directories.
    input: path strings; walk options; extension filter.
    output: report dict with method, files[], totals.
    """
    roots = [Path(p) for p in paths]
    missing = [str(p) for p in roots if not p.exists()]
    cwd = Path.cwd().resolve()

    if all_files:
        exts: frozenset[str] | None = None
    elif extensions:
        normalized: set[str] = set()
        for e in extensions:
            e = e.strip().lower()
            if not e:
                continue
            normalized.add(e if e.startswith(".") else f".{e}")
        exts = frozenset(normalized)
    else:
        exts = _DEFAULT_EXTS

    files = _collect_files(roots, recursive=recursive, exts=exts)
    rows: list[dict[str, object]] = []
    total_tokens = 0
    total_chars = 0
    errors = 0

    for path in files:
        text = _read_text(path)
        display = _display_path(path, cwd)
        if text is None:
            errors += 1
            rows.append(
                {
                    "path": display,
                    "chars": 0,
                    "tokens": 0,
                    "error": "unreadable",
                }
            )
            continue
        n_chars = len(text)
        n_tok = count_tokens(text)
        total_chars += n_chars
        total_tokens += n_tok
        rows.append({"path": display, "chars": n_chars, "tokens": n_tok})

    return {
        "method": token_method(),
        "files": rows,
        "file_count": len(rows),
        "total_chars": total_chars,
        "total_tokens": total_tokens,
        "errors": errors,
        "missing": missing,
    }


def _format_table(report: dict[str, object]) -> str:
    files = report["files"]
    assert isinstance(files, list)
    lines: list[str] = []
    lines.append(f"method: {report['method']}")
    if report.get("missing"):
        for m in report["missing"]:  # type: ignore[union-attr]
            lines.append(f"missing: {m}")
    if not files:
        lines.append("(no files counted)")
        lines.append(f"total: 0 tokens  0 chars  0 files")
        return "\n".join(lines)

    width = max(len(str(r["path"])) for r in files)  # type: ignore[index]
    width = min(max(width, 4), 96)
    lines.append(f"{'tokens':>8}  {'chars':>8}  path")
    lines.append(f"{'-' * 8}  {'-' * 8}  {'-' * min(width, 4)}")
    for row in files:
        if row.get("error"):  # type: ignore[union-attr]
            lines.append(
                f"{'—':>8}  {'—':>8}  {row['path']}  ({row['error']})"  # type: ignore[index]
            )
        else:
            lines.append(
                f"{row['tokens']:>8}  {row['chars']:>8}  {row['path']}"  # type: ignore[index]
            )
    lines.append(
        f"{report['total_tokens']:>8}  {report['total_chars']:>8}  "
        f"TOTAL ({report['file_count']} files)"
    )
    return "\n".join(lines)


def cmd_tokens(args: argparse.Namespace) -> int:
    """
    intent: Print token usage for one or more files/directories.
    input: argparse namespace (paths, flags).
    output: exit 0 on success; 1 if any path missing or unreadable.
    role: subcommand.
    side_effects: reads files; prints stdout.
    """
    report = count_paths(
        list(args.paths),
        recursive=not args.no_recursive,
        all_files=bool(args.all),
        extensions=args.ext,
    )
    if report.get("method") == "heuristic":
        print(
            "note: tiktoken not installed — using heuristic. "
            "For accurate counts: .venv/bin/pip install -r "
            "_okf_knowledge/requirements.txt",
            file=sys.stderr,
        )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_table(report))

    missing = report.get("missing") or []
    errors = int(report.get("errors") or 0)
    if missing or errors:
        return 1
    if int(report.get("file_count") or 0) == 0:
        print("no matching files", file=sys.stderr)
        return 1
    return 0
