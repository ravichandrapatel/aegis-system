#!/usr/bin/env python3
# file_name: okf.py
# description: Thin CLI caller for the Aegis OKF kernel (implementation in kernel/src/).
# version: 1.5.0
# authors: contributors
#
# Usage:
#   python3 _okf_knowledge/kernel/okf.py capabilities [--json] [--strict]
#   python3 _okf_knowledge/kernel/okf.py lookup "<query>" [--card] [--json] [--paths] ...
#   python3 _okf_knowledge/kernel/okf.py pack "<query>" [--style json|markdown|xml]
#   python3 _okf_knowledge/kernel/okf.py card <path> [<path>...]
#   python3 _okf_knowledge/kernel/okf.py compile [--force]
#   python3 _okf_knowledge/kernel/okf.py lint
#   python3 _okf_knowledge/kernel/okf.py enrich [--write] [--only X] [--limit N]
#   python3 _okf_knowledge/kernel/okf.py optimize
#   python3 _okf_knowledge/kernel/okf.py scrape "<query or URL>"
#   python3 _okf_knowledge/kernel/okf.py serve [--port 8080]
"""
intent: One CLI for every kernel operation on the Aegis OKF brain.
role: kernel entry point (caller). Implementation lives in kernel/src/.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure kernel/ is on sys.path so `import src...` works when invoked as a script.
_KERNEL_DIR = Path(__file__).resolve().parent
if str(_KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(_KERNEL_DIR))

from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
