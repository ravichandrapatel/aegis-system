"""Capability discovery probe for portable Aegis pre-flight."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from src.paths import VAULT_ROOT

CapStatus = str  # present | missing | degraded


def _status(present: bool, *, degraded: bool = False, reason: str = "") -> dict[str, str]:
    if not present:
        return {"status": "missing", "detail": reason or "not found"}
    if degraded:
        return {"status": "degraded", "detail": reason or "degraded"}
    return {"status": "present", "detail": reason or "ok"}


def probe_capabilities(repo_root: Path | None = None) -> dict[str, Any]:
    """
    intent: Detect Brain/Filesystem/Python/Git/Shell (+ compile/lint readiness).
    input: optional repo_root (defaults to parent of _okf_knowledge).
    output: capabilities map, enabled_features, runtime_hint.
    role: discovery probe.
    side_effects: none (read-only / PATH checks).
    """
    brain = VAULT_ROOT.resolve()
    root = (repo_root or brain.parent).resolve()

    python_ok = True  # this process is Python
    fs_ok = root.is_dir() and os.access(root, os.R_OK)
    shell_ok = bool(os.environ.get("SHELL") or shutil.which("bash") or shutil.which("sh"))

    kernel_entry = brain / "kernel" / "okf.py"
    vault_dir = brain / "vault"
    standards_dir = brain / "standards"
    brain_present = kernel_entry.is_file() and vault_dir.is_dir() and standards_dir.is_dir()
    brain_degraded = False
    brain_detail = "ok"
    if brain_present:
        graph = brain / "kernel" / "src" / "graph.json"
        if not graph.is_file():
            brain_degraded = True
            brain_detail = "brain tree present but graph.json missing (run compile)"
    else:
        brain_detail = f"missing kernel/okf.py or vault/standards under {brain}"

    git_path = shutil.which("git")
    git_ok = git_path is not None
    if git_ok and not (root / ".git").exists():
        git_status = _status(True, degraded=True, reason="git on PATH but no .git in repo root")
    else:
        git_status = _status(git_ok, reason=git_path or "git not on PATH")

    compile_ready = brain_present and kernel_entry.is_file()
    lint_ready = compile_ready

    caps: dict[str, dict[str, str]] = {
        "python": _status(python_ok, reason=sys.executable),
        "filesystem": _status(fs_ok, reason=str(root)),
        "shell": _status(shell_ok, reason=os.environ.get("SHELL") or shutil.which("bash") or "sh"),
        "brain": _status(brain_present, degraded=brain_degraded, reason=brain_detail),
        "git": git_status,
        "compile": _status(compile_ready, reason="okf.py compile available" if compile_ready else "brain missing"),
        "lint": _status(lint_ready, reason="okf.py lint available" if lint_ready else "brain missing"),
    }

    enabled: list[str] = []
    if caps["filesystem"]["status"] != "missing":
        enabled.append("rung1_inbox")
        enabled.append("advisory_explain")
    if caps["python"]["status"] == "present" and caps["brain"]["status"] in ("present", "degraded"):
        enabled.append("prompt_pack")
        enabled.append("vault_lookup")
    if caps["compile"]["status"] == "present":
        enabled.append("okf_compile")
    if caps["lint"]["status"] == "present":
        enabled.append("okf_lint")
    if caps["compile"]["status"] == "present" and caps["lint"]["status"] == "present":
        enabled.append("rung2_maintain")
    if caps["git"]["status"] in ("present", "degraded"):
        enabled.append("git_ops")

    brain_missing = caps["brain"]["status"] == "missing"
    baseline_missing = any(
        caps[k]["status"] == "missing" for k in ("python", "filesystem", "shell")
    )

    if baseline_missing or brain_missing:
        runtime_hint = "BLOCKED"
    else:
        runtime_hint = "READY"

    return {
        "repo_root": str(root),
        "brain_root": str(brain),
        "capabilities": {k: v["status"] for k, v in caps.items()},
        "details": {k: v["detail"] for k, v in caps.items()},
        "enabled_features": enabled,
        "runtime_hint": runtime_hint,
    }


def format_human(report: dict[str, Any]) -> str:
    """Render a compact capability table for agents/humans."""
    lines = [
        "# OKF Capability Report",
        f"repo: {report['repo_root']}",
        f"brain: {report['brain_root']}",
        f"runtime_hint: {report['runtime_hint']}",
        "",
        "capability\tstatus\tdetail",
    ]
    details = report.get("details", {})
    for name, status in report["capabilities"].items():
        lines.append(f"{name}\t{status}\t{details.get(name, '')}")
    lines.append("")
    feats = ", ".join(report.get("enabled_features") or []) or "(none)"
    lines.append(f"enabled_features: {feats}")
    return "\n".join(lines) + "\n"


def cmd_capabilities(args: Any) -> int:
    """
    intent: CLI entry for capability discovery.
    input: argparse namespace (--json, --strict).
    output: exit 0 normally; exit 4 if --strict and runtime_hint BLOCKED.
    """
    report = probe_capabilities()
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        sys.stdout.write(format_human(report))

    if getattr(args, "strict", False) and report.get("runtime_hint") == "BLOCKED":
        return 4
    return 0
