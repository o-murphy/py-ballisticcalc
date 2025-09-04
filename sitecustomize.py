"""
Development-time environment guardrails for this repository.

When you run Python from the repository root (tests, examples, scripts),
this module is auto-imported by Python's site module. It enforces:

- Disable user site-packages to prevent stale/global shadowing.
- Encourage running inside a virtual environment.
- Optionally assert use of the repo-local .venv unless overridden.

This file is NOT included in distributions; it only affects local dev.
You can bypass strict checks by setting environment variable
PYBC_ALLOW_EXTERNAL_ENV=1.
"""
from __future__ import annotations

import os
import sys
import site
from pathlib import Path


def _find_repo_root_with_venv(start: Path) -> tuple[Path, Path | None]:
    p = start
    while True:
        v = p / ".venv"
        if v.exists():
            return p, v
        if p.parent == p:
            return start, None
        p = p.parent


ROOT, LOCAL_VENV = _find_repo_root_with_venv(Path(__file__).resolve().parent)


def _disable_user_site():
    # Ensure user site-packages are not used or preferred
    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    try:
        user_site = site.getusersitepackages()
    except Exception:
        user_site = None

    if user_site and isinstance(user_site, str):
        user_site_path = Path(user_site).resolve()
        # Remove any sys.path entries that are the user-site or under it
        new_sys_path = []
        for p in sys.path:
            try:
                rp = Path(p).resolve()
            except Exception:
                new_sys_path.append(p)
                continue
            if user_site_path == rp or user_site_path in rp.parents:
                continue
            new_sys_path.append(p)
        sys.path[:] = new_sys_path


def _assert_reasonable_env():
    if os.environ.get("PYBC_ALLOW_EXTERNAL_ENV") == "1":
        return

    in_venv = getattr(sys, "base_prefix", sys.prefix) != sys.prefix

    if not in_venv:
        # If a local .venv exists, provide a strong reminder
        if LOCAL_VENV is not None and LOCAL_VENV.exists():
            msg = (
                "This repository expects commands to run inside its .venv.\n"
                f"Detected interpreter: {sys.executable}\n"
                f"Expected venv under: {LOCAL_VENV}\n\n"
                "Activate the venv first: .\\.venv\\Scripts\\activate\n"
                "Or run via venv explicitly: .\\.venv\\Scripts\\python.exe -m <module>\n\n"
                "To bypass (not recommended), set PYBC_ALLOW_EXTERNAL_ENV=1."
            )
            # Use stderr but do not hard-exit to avoid breaking IDE tooling
            print(msg, file=sys.stderr)
        return

    # If in a venv and a local .venv exists, prefer it; warn if different
    try:
        current_prefix = Path(sys.prefix).resolve()
    except Exception:
        return

    if LOCAL_VENV is not None and LOCAL_VENV.exists():
        try:
            if not current_prefix.is_relative_to(LOCAL_VENV.resolve()):
                print(
                    (
                        "Warning: Active virtualenv is not the repo .venv.\n"
                        f"Active: {current_prefix}\nExpected under: {LOCAL_VENV}\n"
                        "This can lead to shadowing by external packages.\n"
                        "Set PYBC_ALLOW_EXTERNAL_ENV=1 to suppress this message."
                    ),
                    file=sys.stderr,
                )
        except AttributeError:
            # Python <3.9 compatibility (not expected here), fallback check
            local = str(LOCAL_VENV.resolve())
            if not str(current_prefix).startswith(local):
                print(
                    (
                        "Warning: Active virtualenv is not the repo .venv.\n"
                        f"Active: {current_prefix}\nExpected under: {LOCAL_VENV}\n"
                        "This can lead to shadowing by external packages.\n"
                        "Set PYBC_ALLOW_EXTERNAL_ENV=1 to suppress this message."
                    ),
                    file=sys.stderr,
                )


def _ensure_repo_on_path_first():
    # Ensure repository root is at the front of sys.path so local editable
    # sources are importable ahead of any other copies in site-packages.
    root_str = str(ROOT)
    if sys.path[0] != root_str:
        # Remove duplicates first
        sys.path[:] = [p for p in sys.path if p != root_str]
        sys.path.insert(0, root_str)


_disable_user_site()
_ensure_repo_on_path_first()
_assert_reasonable_env()

# Opt-in to Jupyter's platformdirs path scheme on v5, for mkdocs-jupyter.
# This removes the deprecation warning and ensures paths match future defaults.
os.environ.setdefault("JUPYTER_PLATFORM_DIRS", "1")
