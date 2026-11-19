"""The cibuildwheel matrix of a workflow, read from .github/matrices.yml and printed as the JSON for `strategy.matrix`.

    python .github/scripts/wheel_matrix.py exts-tests|ctypes-tests|exts-release

The matrices are long, and the same platforms are in several of them, so they are kept in one file, not in each workflow. A
workflow cannot check what a matrix it reads holds (actionlint sees only the expression), so the entries are checked here: a field
that is missing or not known (a typo in a key would otherwise reach the reusable workflow as an empty value), the type of a
field, an `artifact_key` used twice (the artifact is named from it: two jobs would collide).
"""

import json
import sys
from pathlib import Path

import yaml

MATRICES = Path(__file__).resolve().parent.parent / "matrices.yml"
REQUIRED = {"name": str, "artifact_key": str, "os": str, "cibw_platform": str, "cibw_archs": str, "needs_qemu": bool}
OPTIONAL = {"build": str, "test_skip": str, "timeout_minutes": int}
PLATFORMS = {"linux", "windows", "macos", "pyodide", "android", "ios"}  # the inputs of cibuildwheel-reusable.yml


def check(matrix: str, entries: object) -> list[str]:
    """The problems of one matrix, as messages."""
    if not isinstance(entries, list) or not entries:
        return [f"{matrix}: it must be a list with at least one entry"]
    problems, keys = [], set()
    for number, entry in enumerate(entries, 1):
        where = f"{matrix}[{number}] ({entry.get('name', '?') if isinstance(entry, dict) else entry!r})"
        if not isinstance(entry, dict):
            problems.append(f"{where}: it must be a mapping")
            continue
        for field in REQUIRED.keys() - entry.keys():
            problems.append(f"{where}: `{field}` is missing")
        for field in entry.keys() - REQUIRED.keys() - OPTIONAL.keys():
            problems.append(f"{where}: `{field}` is not a field of an entry")
        for field, kind in (REQUIRED | OPTIONAL).items():
            if field in entry and not isinstance(entry[field], kind):
                problems.append(f"{where}: `{field}` must be {kind.__name__}, not {entry[field]!r}")
        if entry.get("cibw_platform") not in PLATFORMS and "cibw_platform" in entry:
            problems.append(f"{where}: `cibw_platform` {entry['cibw_platform']!r} is not one of {sorted(PLATFORMS)}")
        key = entry.get("artifact_key")
        if key in keys:
            problems.append(f"{where}: `artifact_key` {key!r} is used twice")
        keys.add(key)
    return problems


def main(argv: list[str]) -> int:
    data = yaml.safe_load(MATRICES.read_text(encoding="utf-8"))
    if len(argv) != 2 or argv[1] not in data:
        print(f"::error::usage: wheel_matrix.py {'|'.join(data)}", flush=True)
        return 2
    problems = check(argv[1], data[argv[1]])
    for problem in problems:
        print(f"::error file={MATRICES.name}::{problem}", file=sys.stderr, flush=True)
    if problems:
        return 1
    print(json.dumps({"include": data[argv[1]]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
