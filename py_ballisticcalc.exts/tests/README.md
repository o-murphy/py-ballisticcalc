Cython-specific tests and benchmarks for py-ballisticcalc extensions

- Run the CI helper from PowerShell to build, test, and microbench:

```powershell
./ci_run_cython_checks.ps1
```

- Unit tests live in `test_*.py`.
- Smoke and bench scripts: `smoke_cbase_traj_seq.py`, `bench_append_speed.py`, `microbench.py`.

These are intentionally segregated so repo-root workflows aren't used during quick cython iteration.
