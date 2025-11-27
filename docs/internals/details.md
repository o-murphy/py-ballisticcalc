# Developer Details

This page is for contributors who want to modify algorithms, add engines, or extend the project.

## Recommended one-step dev setup (cross-platform)

=== "Linux / MacOS"
    ```bash
    # create/sync venv with dev + exts
    uv sync --python 3.13 --extra exts

    # activate & test
    source .venv/bin/activate
    pytest --engine="rk4_engine"
    ```

=== "Windows"
    ```powershell
    # create/sync venv with dev + exts
    uv sync --python 3.13 --extra exts

    # activate & test
    .\.venv\Scripts\activate
    pytest --engine="rk4_engine"
    ```

**Notes:**

- The repo includes a `sitecustomize.py` that disables user site-packages and warns if you are not using the local `.venv`, to prevent stale/external packages from shadowing your build.
- If you prefer pip, using `python -m pip install -e ./py_ballisticcalc.exts` (then `python -m pip install -e .`) works fine when the venv is activated.

## CI and `uv.lock`
Development dependencies and reproducible developer/CI installs are pinned in `uv.lock`.

* This lockfile is for maintainers and CI reproducibility; it is not used by library consumers who install via pip/pyproject.
* If you use `uv` for environment management, run `uv sync` (optionally with `--extra exts` to install the Cython subproject) to produce the locked environment used by CI.

## Code locations & responsibilities
- `py_ballisticcalc/` — core Python package.
    - `engines/` — Python engine implementations and `TrajectoryDataFilter`.
    - `trajectory_data.py` — `BaseTrajData`, `TrajectoryData`, `HitResult`, `TrajFlag`, interpolation helpers.
    - `conditions.py`, `munition.py` — shot and environment objects.
    - `drag_model.py`, `drag_tables.py` — drag lookup and interpolation.
- `py_ballisticcalc.exts/` — Cython subproject.
    - `py_ballisticcalc_exts/base_engine.pyx` — Cython wrapper that orchestrates C/C++-layer stepping and defers event logic to Python.
    - `py_ballisticcalc_exts/` `rk4_engine.pyx`, `euler_engine.pyx` — Cython engine implementations.
    - `py_ballisticcalc_exts/*.pyx/*.pxd` — helper functions and bridging helpers for C/C++ structs.

## How engines are wired
Public call flow (simplified):

1. `Calculator.fire()` calls `engine.integrate()`.
2. `BaseIntegrationEngine.integrate()` converts units, calls engine `_integrate()`, which feeds `TrajectoryDataFilter`.
3. `_integrate()` returns a `HitResult` consisting of `TrajectoryData` rows and post-processing functions.

## Testing & parity
- The project runs many parity tests that assert identical results between Python and Cython engines. When adding features, run the whole test suite using the `--engine="engine_name"` argument.
- Focus tests on:
    - Event parity (ZERO_UP/ZERO_DOWN/MACH/APEX) and interpolation accuracy.
    - Search functions (`find_zero_angle`, `find_max_range`, `find_apex`).
    - Dense output correctness (HitResult.base_data) and shape.

## Benchmarking
`scripts/benchmark.py` checks execution speed on two standardized scenarios named `Trajectory` and `Zero`.

!!! note
    If you are contemplating work that could affect performance you should run `benchmark.py` before modifying any code to set a baseline, and then re-run the benchmark afterwards to confirm whether the changes have affected performance.

```bash
# Run benchmarks on all engines:
uv run scripts/benchmark.py --all

# Run benchmarks on specific engine:
uv run scripts/benchmark.py --engine="rk4_engine"
```

### Understanding benchmark results
The benchmark numbers are only meaningful for comparing different versions of the project **run on the same computer** (and under the same operating conditions — i.e., same processor and memory availability).

Each benchmark run will be logged to `./benchmarks/benchmarks.csv`, which will contain a row for each engine and scenario, with the following columns:

* `timestamp` — of the run.
* `version` — of the project (as listed in `pyproject.toml`).
* `branch` — name reported by `git` (if any).
* `git_hash` — version (short) reported by `git`.
* `case` — which scenario was run (`Trajectory` or `Zero`).
* `engine` — which engine was run.
* `repeats` — how many iterations of the case were run to determine runtime statistics.
* `mean_ms` — average runtime (in milliseconds) for the case.
* `stdev_ms` — standard deviation of runtimes observed.
* `min_ms` — fastest runtime observed.
* `max_ms` — slowest runtime observed.

The key statistic to look at is `mean_ms`.  The other three statistics are useful for validating that figure and detecting benchmarking problems.  Ideally:

* **`stdev_ms` should be very small relative to `mean_ms`.**  If it is not then you should check for other processes that could be consuming compute while running the benchmarks and try to disable those.  Alternatively, you can increase the number of iterations used for benchmark by setting a larger `--repeats` argument.  (More samples should reduce the variance from the mean.)
* **`min_ms` and `max_ms` should be similar to `mean_ms`.**  If `max_ms` is much larger than `mean_ms` then you may have other processes competing for compute during the benchmark run.  Or you may need a longer warmup, which you can set with the `--warmup` argument.

## [Cython notes](cython.md) & common pitfalls
- Cython is used only for performance-critical numeric loops. Keep higher-level semantics in Python to avoid code duplication and subtle parity issues.
- Common Cython pitfalls observed in this codebase:
    - Indentation and cdef scoping errors — ensure `cdef` declarations live at the top of a C function or appropriate scope.
    - Avoid using Python booleans when declaring typed C variables (use `bint` and 0/1 assignment in the C context).
    <!-- - Keep initialisation of C structs and memory allocation clear; release resources in `_release_trajectory`. -->

## Build / test commands

=== "pip"
    ```bash
    # optional: install editable C extensions and main package
    py -m pip install -e ./py_ballisticcalc.exts
    py -m pip install -e .

    # run a single test file
    py -m pytest tests/test_exts_basic.py

    # run full tests
    py -m pytest
    ```

=== "uv"
    ```bash
    # install editable C extensions and main package
    uv sync --extra exts
    pytest --engine <engine-entry-path>
    ```


## Where to ask questions
Open an issue on the repository with a minimal reproduction and a note about the engine(s) involved.
