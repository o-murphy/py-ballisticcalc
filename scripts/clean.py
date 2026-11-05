#!/usr/bin/env python3
"""Remove build artifacts of the cythonized extensions.

Usage: python scripts/clean.py [--all]

  --all   also remove .venv and all __pycache__ directories

Afterwards `uv sync --extra exts` rebuilds the extensions.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTS = ROOT / "py_ballisticcalc.exts"
PKG = EXTS / "py_ballisticcalc_exts"


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"removed {path.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="also remove .venv and all __pycache__ directories")
    args = ap.parse_args()

    print("--- Removing extension build artifacts ---")
    targets: list[Path] = [
        ROOT / "py_ballisticcalc_exts.egg-info",
        ROOT / "build",
        ROOT / "dist",
        EXTS / "build",
        EXTS / "dist",
        PKG / "build",
        *EXTS.glob("*.egg-info"),
        *(p for p in PKG.glob("*") if p.is_file() and p.suffix in {".so", ".pyd", ".html"}),
    ]
    for target in targets:
        if target.exists() or target.is_symlink():
            remove(target)

    if args.all:
        print("--- Removing virtual environment and caches ---")
        venv = ROOT / ".venv"
        if venv.exists():
            remove(venv)
        for cache in ROOT.rglob("__pycache__"):
            if ".git" not in cache.relative_to(ROOT).parts and cache.exists():
                remove(cache)
    print("--- Cleanup complete. ---")


if __name__ == "__main__":
    main()
