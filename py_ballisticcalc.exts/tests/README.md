Cython-specific tests and benchmarks for py-ballisticcalc extensions

- Unit tests live in `test_*.py`. Run them from the repository root: `pytest ./py_ballisticcalc.exts/tests` (`-m stress` adds the
  stress tests, which are opt-in).
- Smoke and bench scripts: `smoke_cbase_traj_seq.py`, `bench_append_speed.py`, `microbench.py`.
- CI runs this folder in every wheel test, in the session of every engine, after the core suite (`test-sources` in
  `py_ballisticcalc.exts/pyproject.toml`, `.github/scripts/cibw_run_engines.py`). The `--engine` option is registered by the core
  suite's `conftest.py` there, so this one registers it only when it is not registered yet.

These are intentionally segregated so repo-root workflows aren't used during quick cython iteration.
