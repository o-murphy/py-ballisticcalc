"""Test every engine, one after another, inside a cibuildwheel test environment.

cibuildwheel's test-command runs this from the directory the test sources were copied to:

    python cibw_run_engines.py [group ...]

Expected in cibw_stage/ next to this file (the workflow stages them, nothing here is committed):

    cibw_stage/tests/        the core test suite
    tests/                   the tests of the package under test (its own tests/ folder, when its test-sources list it)
    cibw_stage/core-wheel/   the pure-Python py_ballisticcalc wheel

cibw_stage is deliberately not a package: pytest would then name the tests cibw_stage.tests and `from tests...` in
them would not import. The runner itself is a module of its own (iOS starts it as `python -m cibw_run_engines`).

The core wheel is unpacked and put on the import path instead of being installed: that works the same on every
platform (Android installs binary wheels only, iOS and Pyodide have no pip to call). The exts wheel under test is
already installed by cibuildwheel; its runtime dependencies come from test-requires.

The arguments on the command line pick which engines run: a group (``cython``, ``python``, ``scipy``: the part of the
engine name before the ``+``) or one engine (``python+rk4``); none given means all of them. cibuildwheel tests only ``cython``: the other engines do not depend on the
wheel under test, they are run once per Python version elsewhere (cibuildwheel-tests.yml).

The engines are not listed here and are not probed: they are what the engine loader's entry points name in this
environment (the core wheel's and the exts wheel's), and every one of them is run, so one that cannot load fails
loudly. The only thing left out is a group whose dependency the environment does not have, decided by the
test-requires in pyproject.toml (scipy has no wheels on some platforms and Python versions): it is reported as skipped.
And the exts wheel is the thing under test: if it registered no ``cython+`` engine at all, that is a failure, not a
smaller run.

Each engine is one pytest session (``--engine`` takes one name). A session is a subprocess where there are
subprocesses, and in-process on Pyodide, iOS and Android. An engine does not stop the others: all run, a summary is printed, and the
exit code is non-zero if any failed.
"""

import glob
import importlib.util
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The package's own tests: the tests/ folder of its project, which a package gets into the test environment by listing it in
# its test-sources. They run in the session of every engine, after the core suite, and are told the same --engine.
PACKAGE_TESTS = HERE / "tests"

# No subprocesses (and so no pytest-xdist): Pyodide and iOS have none, and on Android sys.executable is "" (Python is
# embedded in the app), so subprocess fails with PermissionError. The sessions run in this process there.
NO_SUBPROCESS = ("emscripten", "ios", "android")


def unpack_core(wheel_dir: Path) -> str:
    """Unpack the core wheel into a temporary directory and put it first on the import path."""
    wheels = sorted(glob.glob(str(wheel_dir / "py_ballisticcalc-*.whl")))
    if not wheels:
        sys.exit(f"no py_ballisticcalc wheel in {wheel_dir}")
    target = tempfile.mkdtemp(prefix="core-")
    with zipfile.ZipFile(wheels[-1]) as zf:
        zf.extractall(target)
    sys.path.insert(0, target)
    os.environ["PYTHONPATH"] = target + os.pathsep + os.environ.get("PYTHONPATH", "")
    print(f"core wheel: {os.path.basename(wheels[-1])}")
    return target


# the module an engine group needs, when it is not part of the core's own requirements
REQUIRES = {"scipy": "scipy"}


def discover_engines() -> tuple[list[str], list[str]]:
    """Every engine the entry points name, and those left out because their dependency is not installed."""
    from py_ballisticcalc.interface import _EngineLoader as loader

    found, left_out = [], []
    for ep in loader._get_engine_entries():
        engine = loader.engine_id(ep)
        if engine in found or engine in left_out:
            continue
        module = REQUIRES.get(engine.split("+", 1)[0])
        if module and importlib.util.find_spec(module) is None:
            left_out.append(engine)
        else:
            found.append(engine)
    return found, left_out


def select(engines: list[str], wanted: list[str]) -> list[str]:
    """The engines named by the arguments, as groups or as engine names; all of them when there are none."""
    if not wanted:
        return engines
    return [e for e in engines if e in wanted or e.split("+", 1)[0] in wanted]


def can_fork_workers() -> bool:
    """pytest-xdist needs subprocesses: not available where there are none."""
    if sys.platform in NO_SUBPROCESS:
        return False
    # GraalPy on Windows: the first engine's session died in seconds without a word and the second hung for the hour
    # (the CI run of the ctypes wheels); the same suite runs on GraalPy on Linux, so the workers are what is suspected
    if sys.implementation.name == "graalpy" and sys.platform == "win32":
        return False
    return importlib.util.find_spec("xdist") is not None


def run_engine(engine: str, tests: Path, parallel: bool) -> int:
    own = [str(PACKAGE_TESTS)] if PACKAGE_TESTS.is_dir() else []
    args = [str(tests), *own, "-q", "-p", "no:cacheprovider", "-m", "not stress", f"--engine={engine}"]
    if parallel:
        args += ["-n", "auto"]
    if sys.platform in NO_SUBPROCESS:  # run the session in this process
        import pytest

        return int(pytest.main(args))

    return subprocess.call([sys.executable, "-m", "pytest", *args])


def main() -> int:
    tests = HERE / "cibw_stage" / "tests"
    unpack_core(HERE / "cibw_stage" / "core-wheel")

    import py_ballisticcalc

    print(f"py_ballisticcalc {py_ballisticcalc.__version__} from {Path(py_ballisticcalc.__file__).parent}")

    parallel = can_fork_workers()
    print(f"python {sys.version.split()[0]} on {sys.platform}; xdist: {parallel}")

    groups = sys.argv[1:]
    engines, left_out = discover_engines()
    engines, left_out = select(engines, groups), select(left_out, groups)
    print(f"groups: {' '.join(groups) or 'all'}")
    print(f"engines ({len(engines)}): {' '.join(engines) or '-'}")
    for engine in left_out:
        print(f"::notice::SKIP {engine}: its dependency is not installed in this environment")
    if (not groups or "cython" in groups) and not any(e.startswith("cython+") for e in engines):
        print(
            "::error::no cython+ engine is registered: the exts or ctypes wheel under test is not the one in use",
            flush=True,
        )
        return 1
    if not engines:
        print("::error::no engine to run", flush=True)
        return 1

    passed, failed = [], []
    skipped = left_out
    for engine in engines:
        print(f"::group::{engine}", flush=True)
        code = run_engine(engine, tests, parallel)
        print("::endgroup::", flush=True)
        (passed if code == 0 else failed).append(engine)
        if code != 0:
            print(f"FAILED {engine} (exit {code})", flush=True)

    print(f"\npassed {len(passed)}: {' '.join(passed) or '-'}")
    print(f"skipped {len(skipped)}: {' '.join(skipped) or '-'}")
    print(f"failed {len(failed)}: {' '.join(failed) or '-'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
