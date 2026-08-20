"""Allow ``python3 -m okf`` when the brain root is on ``sys.path``."""
from __future__ import annotations

from okf.cli import main

raise SystemExit(main())
