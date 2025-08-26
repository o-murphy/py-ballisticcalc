from __future__ import annotations

import sys
from pathlib import Path


# Ensure the repository root sitecustomize is importable and takes effect
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ROOT_SC = ROOT / "sitecustomize.py"
if ROOT_SC.exists():
    root_str = str(ROOT)
    if sys.path[0] != root_str:
        sys.path[:] = [p for p in sys.path if p != root_str]
        sys.path.insert(0, root_str)
    # Import triggers guardrails
    import sitecustomize  # noqa: F401
