Cython-specific tests and benchmarks for py-ballisticcalc extensions

- Unit tests live in `test_*.py`. Run them from the repository root: `pytest ./py_ballisticcalc.exts/tests` (`-m stress` adds the
  stress tests, which are opt-in).
- Smoke and bench scripts: `smoke_cbase_traj_seq.py`, `bench_append_speed.py`, `microbench.py`.
- CI runs this folder in every wheel test, in the session of every engine, after the core suite (`test-sources` in
  `py_ballisticcalc.exts/pyproject.toml`, `.github/scripts/cibw_run_engines.py`). The `--engine` option is registered by the core
  suite's `conftest.py` there, so this one registers it only when it is not registered yet.

Under AddressSanitizer the RSS check of `test_memory_leak.py` (`-m stress`) fails: ASan keeps freed blocks in its quarantine (256 MB by
default), so RSS grows without a leak. Run it with `ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=1` (and `PYTHONMALLOC=malloc`,
`LD_PRELOAD` of libasan/libubsan as for any sanitized extension).

These are intentionally segregated so repo-root workflows aren't used during quick cython iteration.
