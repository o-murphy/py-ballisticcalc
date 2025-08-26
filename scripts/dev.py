#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "uv>=0.4"
# ]
# ///
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    venv = repo / ".venv"
    py = os.environ.get("PYTHON", "3.12")
    recreate = os.environ.get("RECREATE", "0") == "1"

    if not shutil.which("uv"):
        raise SystemExit("uv is required. Install from https://docs.astral.sh/uv/ and re-run.")

    if recreate and venv.exists():
        shutil.rmtree(venv)

    # Create/sync env and dependencies using uv. This will create .venv.
    run(["uv", "sync", f"--python={py}", "--dev", "--extra", "exts"])  # relies on [tool.uv.sources]

    # Force editable installs of local projects into the target venv
    run(["uv", "pip", "install", "-p", str(venv), "-e", str(repo / "py_ballisticcalc.exts")])
    run(["uv", "pip", "install", "-p", str(venv), "-e", str(repo)])

    print("\nDev environment ready.")
    print("Activate:")
    if os.name == "nt":
        print("  .\\.venv\\Scripts\\activate")
    else:
        print("  source .venv/bin/activate")
    print("Run tests:")
    print("  python -m pytest tests")


if __name__ == "__main__":
    main()
