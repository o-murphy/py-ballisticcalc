"""Where the bclibc sources are, how they are staged, and bclibc/version.h without CMake.

The repository has one bclibc submodule, at the top level (``bclibc/``).
This package does not have a copy of its own; it finds the sources in one of two places:

* ``py_ballisticcalc_exts/external/bclibc``: the staged copy. ``sdist`` puts it into the source distribution, so
  that one builds anywhere, and ``python _bclibc.py stage`` makes it for a build that sees only this directory
  (cibuildwheel runs a Linux build in a container with the project directory only). It is not committed.
* the repository's submodule, when building from the repository.

A staged copy carries a ``BCLIBC_VERSION`` file (the ``git describe`` of the submodule): a copy has no git history.

usage: python _bclibc.py stage [<destination>]
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGED = HERE / "py_ballisticcalc_exts" / "external" / "bclibc"
# where the repository's one submodule is: the top level
SUBMODULES = (HERE.parent / "bclibc",)


def shared() -> Path:
    """The repository's bclibc submodule (the first place that has its sources)."""
    for candidate in SUBMODULES:
        if (candidate / "src" / "ffi" / "bclibc_ffi.cpp").exists():
            return candidate
    return SUBMODULES[0]


# what the library is built from, and what the sdist needs
COPY = ("include", "src", "version.h.in", "LICENSE")
DEFAULT_VERSION = (0, 1, 0)


def bclibc_dir() -> Path:
    """The staged copy if there is one, else the shared submodule."""
    for candidate in (STAGED, shared()):
        if (candidate / "src" / "ffi" / "bclibc_ffi.cpp").exists():
            check_header(candidate)
            return candidate
    raise RuntimeError(
        "bclibc sources not found: run `git submodule update --init --recursive` in the repository, "
        f"or `python _bclibc.py stage` ({shared()})"
    )


REQUIRED_SYMBOL = "BCLIBCFFI_integrate_dense_shot_stats"


def check_header(directory: Path) -> None:
    """Fail early with a clear message when the bclibc checkout is older than the C ABI this package declares."""
    header = directory / "include" / "bclibc" / "ffi" / "bclibc_ffi.h"
    if REQUIRED_SYMBOL not in header.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError(
            f"{header} has no {REQUIRED_SYMBOL}: the bclibc checkout is too old for py_ballisticcalc_exts "
            "(update the bclibc submodule)"
        )


def describe(directory: Path) -> str:
    """git describe of the bclibc checkout, or the version file a staged copy carries ('' when neither)."""
    marker = directory / "BCLIBC_VERSION"
    if marker.exists():
        return marker.read_text().strip()
    try:
        return subprocess.run(
            ["git", "describe", "--tags", "--always"], cwd=directory, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def bclibc_version(directory: Path) -> tuple[str, int, int, int]:
    """(version string, major, minor, patch), by the rules of bclibc's CMakeLists.txt.

    A describe output that starts with a semantic version gives the numbers from it and the string without the leading
    "v"; any other output (a bare hash) gives 0.1.0-git-<describe>; nothing gives 0.1.0-dev.
    """
    text = describe(directory)
    if not text:
        return ("0.1.0-dev", *DEFAULT_VERSION)
    match = re.match(r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)", text)
    if match:
        return (re.sub(r"^v", "", text), int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (f"0.1.0-git-{text}", *DEFAULT_VERSION)


def write_version_header(directory: Path, out_dir: Path) -> Path:
    """Write out_dir/bclibc/version.h from bclibc's version.h.in; return the include directory (out_dir)."""
    version, major, minor, patch = bclibc_version(directory)
    text = (
        (directory / "version.h.in")
        .read_text()
        .replace("@BCLIBC_VERSION_MAJOR@", str(major))
        .replace("@BCLIBC_VERSION_MINOR@", str(minor))
        .replace("@BCLIBC_VERSION_PATCH@", str(patch))
        .replace("@BCLIBC_VERSION@", version)
    )
    if "@BCLIBC_" in text:
        raise RuntimeError("version.h.in has placeholders this generator does not fill")
    target = out_dir / "bclibc" / "version.h"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text if text.endswith("\n") else text + "\n")
    return out_dir


def stage(destination: Path = STAGED) -> Path:
    """Copy the shared submodule's sources (and its version) to destination, replacing what is there."""
    source = shared()
    if not (source / "src").exists():
        raise RuntimeError(f"the bclibc submodule is empty: run `git submodule update --init --recursive` ({source})")
    version = describe(source)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name in COPY:
        item = source / name
        if item.is_dir():
            shutil.copytree(item, destination / name)
        elif item.exists():
            shutil.copy2(item, destination / name)
    (destination / "BCLIBC_VERSION").write_text((version or "") + "\n")
    return destination


def unstage(destination: Path = STAGED) -> None:
    shutil.rmtree(destination, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "stage":
        print(stage(Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else STAGED))
    else:
        sys.exit(__doc__)
