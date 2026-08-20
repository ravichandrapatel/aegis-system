#!/usr/bin/env python3
# file_name: okf.py
# description: CLI entry for the okf package (lives under kernel/).
# version: 1.9.0
# authors: contributors
#
# Usage (from repo root — directory that contains AGENTS.md):
#   python3 _okf_knowledge/kernel/okf.py pack "<query>"
#   python3 _okf_knowledge/kernel/okf.py compile
#   python3 _okf_knowledge/kernel/okf.py lint
"""
intent: Stable CLI path for agents and humans.
role: thin entrypoint — implementation lives in the `okf` package.
"""
from __future__ import annotations

import sys
from pathlib import Path

# This file's directory (kernel/) must be on sys.path so `import okf` works.
_tooling_dir = Path(__file__).resolve().parent
if str(_tooling_dir) not in sys.path:
    sys.path.insert(0, str(_tooling_dir))

from okf.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
