# file_name: style.py
# description: AST naming checks for the OKF runtime package (standards/python-naming).
# version: 1.0.0
# authors: contributors
"""Enforce single-style identifiers under the okf package."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from okf.paths import CLI_SCRIPT, PACKAGE_DIR, VAULT_ROOT

_LOWER_SNAKE = re.compile(r"^_?[a-z][a-z0-9_]*$")
_UPPER_SNAKE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
_CAP_WORDS = re.compile(r"^_?[A-Z][A-Za-z0-9]*$")
_DUNDER = re.compile(r"^__[a-z]+__$")
_BANNED_PREFIX = re.compile(r"^(okf_|OKF_|kernel_|KERNEL_)")
# stdlib BaseHTTPRequestHandler requires do_GET / do_POST / …
_HTTP_VERB = re.compile(r"^do_[A-Z][A-Z0-9_]*$")


def _is_lower_snake(name: str) -> bool:
    return bool(_LOWER_SNAKE.match(name) or _DUNDER.match(name) or _HTTP_VERB.match(name))


def _is_upper_snake(name: str) -> bool:
    return bool(_UPPER_SNAKE.match(name))


def _is_cap_words(name: str) -> bool:
    return bool(_CAP_WORDS.match(name)) and "_" not in name.lstrip("_")


def _banned_prefix(name: str) -> bool:
    return bool(_BANNED_PREFIX.match(name))


def _style_ok_for_class(name: str) -> bool:
    return _is_cap_words(name)


def _style_ok_for_func(name: str) -> bool:
    return _is_lower_snake(name)


def _style_ok_for_binding(name: str) -> bool:
    """Module/local binding: lower_snake, UPPER_SNAKE, or CapWords (type alias)."""
    return _is_lower_snake(name) or _is_upper_snake(name) or _is_cap_words(name)


def _rel_concept(path: Path) -> str:
    try:
        return str(path.relative_to(VAULT_ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


def _scan_tree(tree: ast.AST, path: Path) -> list[dict[str, str]]:
    """
    intent: Walk a module AST and emit naming findings.
    input: parsed tree and source path.
    output: list of finding dicts (severity/concept/code/message).
    role: pure checker.
    side_effects: none.
    """
    findings: list[dict[str, str]] = []
    concept = _rel_concept(path)

    def add(code: str, lineno: int, message: str) -> None:
        findings.append(
            {
                "severity": "error",
                "concept": concept,
                "code": code,
                "message": f"line {lineno}: {message}",
            }
        )

    def check_name(name: str, lineno: int, *, kind: str) -> None:
        if name == "_":
            return
        if _banned_prefix(name):
            add(
                "DBG-321",
                lineno,
                f"{kind} '{name}' uses banned product prefix "
                "(okf_/OKF_/kernel_/KERNEL_) — see standards/python-naming.md",
            )
            return
        if kind == "class" and not _style_ok_for_class(name):
            add(
                "DBG-320",
                lineno,
                f"class '{name}' must be CapWords — see standards/python-naming.md",
            )
            return
        if kind == "function" and not _style_ok_for_func(name):
            add(
                "DBG-320",
                lineno,
                f"function '{name}' must be lower_snake — see standards/python-naming.md",
            )
            return
        if kind == "binding" and not _style_ok_for_binding(name):
            add(
                "DBG-320",
                lineno,
                f"name '{name}' must be lower_snake, UPPER_SNAKE, or CapWords "
                "(one style only) — see standards/python-naming.md",
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            check_name(node.name, node.lineno, kind="class")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            check_name(node.name, node.lineno, kind="function")
            for arg in list(node.args.posonlyargs) + list(node.args.args) + list(
                node.args.kwonlyargs
            ):
                check_name(arg.arg, getattr(arg, "lineno", node.lineno), kind="binding")
            if node.args.vararg is not None:
                check_name(node.args.vararg.arg, node.lineno, kind="binding")
            if node.args.kwarg is not None:
                check_name(node.args.kwarg.arg, node.lineno, kind="binding")
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets: list[ast.expr]
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    check_name(target.id, node.lineno, kind="binding")
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            check_name(elt.id, node.lineno, kind="binding")
    return findings


def check_package_naming() -> list[dict[str, str]]:
    """
    intent: Lint identifier style for the runtime package and CLI shim.
    input: none (reads PACKAGE_DIR + sibling okf.py).
    output: finding dicts ready to merge into vault lint.
    role: standards/python-naming enforcer.
    side_effects: reads .py files under the package.
    """
    roots = [PACKAGE_DIR]
    shim = CLI_SCRIPT
    findings: list[dict[str, str]] = []
    files: list[Path] = []
    for root in roots:
        files.extend(sorted(root.rglob("*.py")))
    if shim.is_file():
        files.append(shim)
    for path in files:
        if "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            findings.append(
                {
                    "severity": "error",
                    "concept": _rel_concept(path),
                    "code": "DBG-320",
                    "message": f"cannot parse for naming lint: {exc}",
                }
            )
            continue
        findings.extend(_scan_tree(tree, path))
    return findings
