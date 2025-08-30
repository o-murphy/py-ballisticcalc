"""Run doctests across the py_ballisticcalc package.

This helper discovers all non-package modules under `py_ballisticcalc`
and executes their docstring tests using `doctest` with the ELLIPSIS
option enabled. Package `__init__.py` files are intentionally skipped to
avoid relative-import issues when doctested as standalone modules.

Usage (run from repo root):
        - python scripts/run_doctest.py
        - python -m scripts.run_doctest

Behavior:
        - Imports each module via importlib; on import error, prints
            `IMPORT-ERROR <module> <exception>` and continues.
        - Aggregates failures and attempts, printing a final summary line
            `TOTAL <failures> <attempted>`.
        - Exits with code 1 if any doctests fail, else exits with 0.

This script is CI-friendly and can be wired into pipelines to enforce that
examples in docstrings stay correct and up to date.
"""

import doctest, pkgutil, sys, pathlib, importlib

def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1] / 'py_ballisticcalc'
    mods = [m.name for m in pkgutil.walk_packages([str(root)], prefix='py_ballisticcalc.') if not m.ispkg]
    fails = 0
    tried = 0
    for name in sorted(mods):
        if name.endswith('__init__'):
            continue
        try:
            m = importlib.import_module(name)
        except Exception as e:
            print('IMPORT-ERROR', name, e)
            continue
        r = doctest.testmod(m, optionflags=doctest.ELLIPSIS)
        tried += r.attempted
        fails += r.failed
        if r.failed:
            print(f'FAIL {name}: {r.failed}/{r.attempted}')
    print('TOTAL', fails, tried)
    return int(fails > 0)

if __name__ == '__main__':
    raise SystemExit(main())
