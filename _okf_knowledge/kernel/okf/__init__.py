"""
OKF runtime — local knowledge pack / compile / lint.

Prefer the CLI shim or module form:

    python3 _okf_knowledge/kernel/okf.py pack \"<query>\"
    python3 -m okf pack \"<query>\"   # from kernel/ with PYTHONPATH=.
"""

from __future__ import annotations

__version__ = "1.9.0"
__all__ = ["__version__"]
