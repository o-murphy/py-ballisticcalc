# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `examples/tiny_bclibc_wasm`: `TinyBclibcWasmDoubleIntegrationEngine`/`TinyBclibcWasmSingleIntegrationEngine`,
  the WebAssembly counterpart of `examples/tiny_bclibc_ctypes`, made for Pythonista on iOS. It runs
  bclibc's import-free tiny_bclibc `.wasm` build (`tiny_bclibc/build_wasm.sh`) inside a JavaScript
  engine: JavaScriptCore's `JSContext` via `objc_util` on iOS, WebKitGTK's JavaScriptCore via
  PyGObject on Linux (`run_example_jsc.py`), or Node. The same JS glue runs on all three hosts, and
  one engine call is one JS round trip. The double-precision engine passes the full suite and
  returns results bit-identical to the native ctypes engine; the single-precision one has the same
  known float32 exceptions as its ctypes twin. Building the modules needs a bclibc submodule that
  includes `tiny_bclibc/build_wasm.sh`.

## [3.0.0-rc.1] - 2026-09-22

### Fixed
- `cython.rkck`/`cython.dopri`/`cython.tsitouras`: bumped the
  `bclibc` submodule to pick up its `BCLIBC_CashKarpIntegrator`/`BCLIBC_DormandPrinceIntegrator`/
  `BCLIBC_TsitourasIntegrator` classes, replacing the old thread-local tolerance/step-count API
  (`BCLIBC_cashKarpSetRelativeTolerance`/`BCLIBC_cashKarpGetStats`/etc.). Each engine instance now
  owns its own integrator (obtained via `std::function::target()` once `integrate_func` has taken a
  copy of it), instead of every instance of the same adaptive engine on a thread sharing one
  `thread_local` tolerance/step-count pair — a latent bug that could silently mix up tolerances or
  accepted/rejected counts between engine instances run concurrently on the same thread (these
  modules are all `freethreading_compatible`). No change to the public Python API: `relative_tolerance`,
  `absolute_tolerance`, and `get_step_stats()` behave the same as before.
- `Calculator._EngineLoader._is_legacy_name` now `@functools.cache`s like its sibling lookups
  (`_get_entries_by_group`, `_get_engine_entries`, `_load_by_name`) instead of being the one
  method in that class that re-walked `iter_engines()` (generator, `seen`-set, per-entry
  `engine_id()`) on every call — wasted, repeated work when many `Calculator` instances are
  created in a loop with the same `engine=` string, since `entry_points()` itself doesn't change
  within a process.
- `vector.py`/`unit.py`: removed 15 of 22 `# type: ignore[override]` comments on arithmetic dunder
  overrides (`Temperature.__mul__`/`__rmul__`/`__truediv__`/`__rtruediv__`/`__imul__`/
  `__itruediv__`/`_units_to_raw_delta`/`__radd__`/`__rsub__`, `Vector.__radd__`/`__iadd__`/
  `__sub__`/`__isub__`/`__imul__`/`__neg__`) that no longer suppress any pyright diagnostic —
  confirmed by removing each individually and re-running `pyright` clean. The remaining 7
  (`Temperature.__add__`/`__sub__`/`__iadd__`/`__isub__`, `Vector.__mul__`/`__add__`/`__rmul__`)
  do still suppress a real `reportIncompatibleMethodOverride` (their `Number`/`Vector` parameter
  types are narrower than `tuple`'s/`GenericDimension`'s own) and were left in place.

### CI
- `.pre-commit-config.yaml`: the `uv-lock`/`uv-lock-exts` hooks now run `uv lock --check` instead
  of `uv lock --upgrade`. `--upgrade` re-resolved to whatever was newest on PyPI *at CI run
  time*, so a transitive dependency (not even a direct one — `platformdirs`/`virtualenv`, pulled
  in by `pre-commit`/`uv` themselves) getting a new release between commits failed
  `pre-commit.yml`'s push-triggered runs with no code change involved (its auto-commit-fixes step
  only runs on `pull_request` events, so a `push` run just fails outright — see
  [bclibc-functors CI run 35705018507](https://github.com/o-murphy/py-ballisticcalc/actions/runs/35705018507)
  for an example). `--check` only verifies `uv.lock` still matches `pyproject.toml`'s own
  constraints; routine dependency bumps are already Dependabot's job (`.github/dependabot.yml`,
  weekly).

## [3.0.0-beta.3] - 2026-09-21

### Added
- New entry point model: engines are registered in groups `py_ballisticcalc.engines.<engine>`
  (`python`, `cython`, `scipy`) with the integration method as the entry point name, and are
  selected with `<engine>+<method>` or `<engine>.<method>` (e.g. `Calculator(engine="cython+rk4")`,
  `"scipy+dop853"`). The direct `<module>:<factory>` path is still supported, including the
  call form `"py_ballisticcalc:SciPyIntegrationEngineFactory(method=DOP853)"`.
- `SciPyIntegrationEngineFactory(method)` and ready-made `SciPy<Method>IntegrationEngine` factories
  (RK23, RK45, DOP853, Radau, BDF, LSODA) in `py_ballisticcalc.engines`.
- Typed configs `DormandPrinceEngineConfig` and `TsitourasEngineConfig` (type stubs) alongside
  `CashKarpEngineConfig`; all three adaptive Cython engines now expose the same stub API.
- `scripts/bench_report.py`: builds the benchmark page from `benchmarks/benchmarks.csv` — grouped
  log-scale bar charts of mean time and of speedup vs `python.rk4` (`docs/concepts/bench.svg`,
  `docs/concepts/bench_speedup.svg`) plus a results table (`docs/concepts/bench.md`, added to the docs nav).
- Benchmarks for all `scipy+…` methods (RK23, RK45, DOP853, Radau, BDF, LSODA), `python+euler` and `python+verlet`.

### Changed
- `_EngineLoader.iter_engines()` deduplicates entries by target; new `_EngineLoader.engine_id(ep)`.
- `scripts/benchmark.py`, `examples/performance_check.py`, tests and CI use the new engine names.
- `README.md` and `docs/`: engine tables show the per-engine speed for the new names, with a separate row and
  description for every `scipy+…` method and a per-engine "Tests" badge column; the engine test badges above
  the table were moved into it.
- Engine speed figures in the tables were re-measured (Find Zero / Trajectory vs `python+rk4`): Cython
  adaptive engines 2567x / 326x, `scipy+rk45` 5.4x / 9.8x, and so on. `cython+verlet` is not re-measured yet.
- SciPy engine: cut Python-side overhead per call without changing tolerances (no per-call `Velocity`
  object in `get_density_and_mach_for_altitude`, safeguarded Newton instead of `brentq` for the
  range-step interpolation, plain math instead of numpy in the terminating events, scalar indexing in
  `diff_eq`, `warnings.simplefilter` applied once at import). A 2000 m RK45 trajectory takes ~11 ms instead of
  ~19 ms. As a side effect DOP853's zero-angle solver no longer stalls just above `cZeroFindingAccuracy`,
  which removes the repeated `Failed to find zero angle using Newton method` warnings.

### Deprecated
- The legacy flat entry point group `py_ballisticcalc` (`euler_engine`, `rk4_engine`, `scipy_engine`,
  `cythonized_*_engine`, ...). Loading an engine by these names emits a `DeprecationWarning`.

## [3.0.0-beta.2] - 2026-09-21

### Added
- `cythonized_tsitouras_engine` (`py_ballisticcalc_exts.CythonizedTsitourasIntegrationEngine`):
  a compiled Tsitouras 5(4) ("Tsit5") adaptive engine, wrapping
  [bclibc](https://github.com/ballistics-lab/bclibc)'s new `BCLIBC_integrateTsitouras`.
  Structurally identical to `cythonized_dopri_engine` (same 7-stage FSAL shape, same SciPy
  RK45-style component scaling and controller); coefficients verified against
  `ARKODE_TSITOURAS_7_4_5` in SUNDIALS/ARKODE. Measured against `cythonized_rkck_engine` and
  `cythonized_dopri_engine` across a sweep of shot profiles: accepted+rejected step counts come
  out within 1-2 steps of each other for smooth, well-conditioned trajectories at
  `rtol=atol=1e-6` — no consistent win, despite Tsitouras' smaller leading truncation-error
  coefficient.

### Changed
- Bumped the `bclibc` submodule to pick up its own new `BCLIBC_integrateTsitouras`, an FFI
  unknown-method-fallback fix (unrecognized/out-of-range method now falls back to RK4, not
  Euler), and `tiny_bclibc`'s internal switch from Cash-Karp to Tsitouras as its baked-in
  adaptive core (`examples/tiny_bclibc`'s two engines pick this up automatically). See
  [bclibc's CHANGELOG](https://github.com/ballistics-lab/bclibc/blob/main/CHANGELOG.md) for
  details. Further bumped to pick up a fix aligning `tiny_bclibc`'s per-stage Tsitouras
  accumulation order with the C++ engine's (identity-test diffs on a simple shot now at the
  double-precision noise floor, down from ~1e-9) -- `TinyBclibcSingleIntegrationEngine`'s
  docstring here has been updated to match (two new single-precision-only marginal test
  failures, `test_wind_lag_rule`/`test_multiple_wind`, same precision-floor class as the rest
  of that list). Bumped once more to pick up a genuine fix (not just closer rounding) for
  `test_hitresult.py::test_flags`, previously `TinyBclibcDoubleIntegrationEngine`'s one known
  failure: `tiny_bclibc`'s MACH-crossing interpolation linearly interpolated the mach *ratio*
  itself instead of reconstructing it from Hermite-derived velocity and a linearly-interpolated
  speed of sound like the C++ engine does, costing real accuracy right at MACH crossings
  (worst in the transonic region). `test_flags` now passes under
  `TinyBclibcDoubleIntegrationEngine`; its docstring's known-issue note has been removed.

## [3.0.0-beta.1] - 2026-09-17
[:simple-github: Diff since v2.3.1][3.0.0-beta.1]

### Changed
- Pin `bclibc` to `v2.0.0-beta.7`, including the zero-point result API and
  its corrected WASM export metadata.
- `cythonized_rkck_engine`: Cash-Karp's adaptive error controller now has
  `scipy.integrate.solve_ivp` semantics. `absolute_tolerance` is a single scalar (default
  `1e-6`) used independently for all six position/velocity state components; it replaces the
  former hidden, unequal position and velocity floors. Each component uses
  `atol + rtol * max(abs(y), abs(y_new))`, and the controller accepts/rejects steps using the
  RMS of those six scaled errors. `relative_tolerance` remains scalar and defaults to `1e-6`.

### Added
- `cythonized_dopri_engine`, a compiled Dormand--Prince 5(4) adaptive engine.
  Its component scaling and controller factors follow SciPy RK45, while
  `cythonized_rkck_engine` deliberately retains its historical controller.
- `cythonized_rkck_engine` (`py_ballisticcalc_exts.CythonizedCashKarpIntegrationEngine`): a
  Cython engine wrapping [bclibc](https://github.com/ballistics-lab/bclibc)'s new Cash-Karp
  adaptive RK45 integrator (Numerical Recipes' `rkck`, embedded 4th/5th-order error estimate).
  Grows its internal step up to 64x the configured base step during smooth flight and shrinks
  it on error-estimate rejection, needing far fewer accepted steps than fixed-step RK4 for
  comparable accuracy — benchmarked at 2.1x (`Trajectory`) / 14.3x (`Zero`, which integrates
  repeatedly per Newton iteration, so per-call step-count savings compound) faster than
  `cythonized_rk4_engine` on the standard 2000m G7 benchmark shot. Exposes a
  `relative_tolerance` config option (default `1e-6`, empirically Pareto-optimal on the one
  shot profile measured so far — see the engine's `__init__` docstring and
  `tests/test_cashkarp.py::test_cashkarp_accuracy_across_tolerances` for the data; height/
  velocity accuracy plateaus below this, but event-root distance accuracy is *not* monotonic in
  tolerance) and a `get_step_stats()` method returning this instance's own
  `(accepted, rejected)` step counts from its most recent `integrate()` call.
- `examples/tiny_bclibc/`: single- and double-precision `BaseIntegrationEngine` subclasses
  (`TinyBclibcSingleIntegrationEngine` / `TinyBclibcDoubleIntegrationEngine`) driving
  [bclibc](https://github.com/ballistics-lab/bclibc)'s `tiny_bclibc` C99 engine via ctypes
  and `tiny_bclibc_integrate_stream`, a filtered-trajectory-streaming API added to
  `tiny_bclibc` for this purpose: both the integration and its range-step/APEX/MACH/ZERO
  filtering and derived-field computation run in the compiled library, with Python's callback
  firing once per *output* row rather than once per raw integration step (a
  `tiny_bclibc_integrate_raw` raw-per-step variant was tried first and is ~20-34x slower — kept
  in `tiny_bclibc` as a small, generically useful primitive, but not used by these engines).
  `tiny_bclibc_integrate`/`_stream` now run `tiny_bclibc`'s own Cash-Karp adaptive core (see
  `bclibc`'s CHANGELOG) rather than fixed-step RK4; `zero_angle`/`find_apex`/`find_max_range`
  are still `BaseIntegrationEngine`'s own unmodified Python implementations, repeatedly calling
  `_integrate`. `CMakeLists.txt` builds both precisions from the `bclibc` git submodule already
  vendored for the Cython engine at
  `py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc`. Running both engines against
  the full pytest suite separates precision effects from logic bugs: the double-precision
  engine passes the entire suite identically to `rk4_engine`/`cythonized_rk4_engine` (373
  passed, 8 skipped); the single-precision engine differs on 13 of 381 tests, all traceable to
  float32's representable precision (8 compare `tiny_bclibc_integrate_stream`'s
  `range_limit_ft`/`range_step_ft` request fields, themselves `real_t`, against a
  double-precision-tight tolerance; the remainder compare values within a few ULPs of float32's
  precision floor, including two whose adaptive step-size selection is itself sensitive to
  sub-ULP differences between two numerically-equivalent drag models — see
  `TinyBclibcSingleIntegrationEngine`'s docstring for the verified mechanism behind each). Not
  wired into `py_ballisticcalc`'s own entry points/public API — it depends on a
  natively-compiled library the package does not ship or build itself.

### Changed
- `HitResult.records`/`_common.py`'s `_sort_rows` (formerly `_coalesce_rows`): a scheduled
  RANGE-step sample and a physical event (ZERO/MACH/APEX) that happen to fall at nearly the
  same instant are no longer merged into one row with combined flags — they are kept as
  independent records, only re-sorted into chronological order (each was already correctly
  positioned relative to *its own* neighbors; only cross-interval ordering needed restoring).
  `HitResult.samples`'s own "annotate the closest scheduled sample with each event's flag"
  projection already performs the equivalent view generically from independent records (see
  `docs/concepts/trajectory_data.md`), so pre-merging here duplicated — and could conflict
  with — that step. Matches the same fix applied to `TrajectoryDataFilter.record_step` and
  bclibc's C++ `BCLIBC_TrajectoryDataFilter::handle_step` (project issue #350).
- **BREAKING:** `HitResult.__len__`/`__iter__`/`__getitem__`, `dataframe()`, and `plot()` now
  read from `records` (the exact chronological stream) instead of the old `trajectory`
  presentation table. Concretely: `len(hit_result)`, `for row in hit_result`, and
  `hit_result[i]` now include every exact ZERO/MACH/APEX/MRT event row in its own chronological
  position, rather than folding its flag onto the nearest RANGE-scheduled sample. Renamed the
  old `trajectory` presentation view (fixed cardinality tracking the requested RANGE/TIME
  schedule regardless of solver internals — see `test_cashkarp_tolerance_controls_adaptive_step_count`)
  to `samples`, so it stays available under an explicit name for anyone comparing output across
  engines or tolerances. `HitResult.trajectory` itself is kept as a deprecated alias for
  `records` (see Deprecated below) so existing attribute access keeps working, just with a
  different row count/order than before if event flags were requested; code that indexed
  `.trajectory` assuming the fixed RANGE/TIME schedule should switch to `.samples`.

- `HitResult.base_data` (pure-Python engines: `euler`/`rk4`/`velocity_verlet`) is a flat
  `list[BaseTrajData]` again — one entry per accepted-step point, matching both the
  pre-`records`/`samples`/`events` shape and bclibc's own `BCLIBC_BaseTrajSeq` (also a flat
  buffer of points). It had briefly become `list[TrajectoryStep]` (each step's `start`/`end`
  pair materialized up front) during this same unreleased work — `TrajectoryStep` is a
  computational helper for one interval, not a storage shape, and pre-pairing every entry
  duplicated each interior point across its neighboring pairs for no benefit over building a
  `TrajectoryStep` on demand from `zip(base_data, base_data[1:])` at query time, which
  `HitResult.interpolate()`/`get_at()` now do. `TrajectoryDataFilter.record_step()` similarly
  takes `(start, end)` directly instead of a pre-built `TrajectoryStep`, constructing one
  internally; callers (the three pure-Python engines) no longer need to import `TrajectoryStep`
  at all. Cython/`dense_output` engines are unaffected — they already exposed their own
  `CythonizedBaseTrajSeq` (a flat buffer with its own `get_at()`), never `TrajectoryStep`.
- `HitResult.__init__` drops the `trajectory=` keyword-only compatibility spelling introduced
  earlier in this same unreleased work: `records` is now an ordinary, required positional
  parameter. `HitResult` is built internally by the engines (always positionally) and is not
  meant to be constructed directly by user code, so a back-compat spelling for a former public
  dataclass constructor had no real caller to protect.

### Deprecated
- `HitResult.trajectory`: alias for `HitResult.records` retained for source compatibility
  (emits `DeprecationWarning`). Use `.records` for the exact chronological stream, or `.samples`
  for the deterministic scheduled-sample table (what `.trajectory` used to mean before this
  release's `records`/`samples`/`events` split).

### Fixed
- fix: pure python `start_from_time` regression
- `py_ballisticcalc/trajectory_data.py`: `HitResult.samples` annotated the *nearest* scheduled
  sample with every event's flag unconditionally, with no check that the two were actually
  close. With a coarse schedule (e.g. `trajectory_step == trajectory_range`, leaving only the
  launch and terminal samples) and `flags=TrajFlag.ALL`, every event in between — APEX, ZERO,
  MACH — landed on whichever endpoint bisection preferred, producing one row with a nonsensical
  combined flag (e.g. `ZERO_DOWN|RANGE|APEX`) that misrepresented that endpoint's own state as
  every event's. `samples` now annotates a sample only when `math.isclose()` (using the new
  `_SAME_INSTANT_REL_TOL`/`_SAME_INSTANT_ABS_TOL` constants) judges the sample and the event to
  be the same instant to floating-point precision — the genuine case this exists for (e.g. a
  RANGE sample requested at the same distance a zero was set for, reached by two different
  numerical paths that agree to solver residual) — rather than merely the closest of however
  many samples happen to exist. A relative tolerance (not the engines' own tolerance knobs,
  which use incompatible units — feet for `cZeroFindingAccuracy`, a state-error rtol for
  `relative_tolerance`, a step-size multiplier for `cStepMultiplier`, none of them a time
  tolerance) keeps the check independent of flight-time scale and any specific engine's
  precision, while staying far tighter than the gap between any two physically distinct
  trajectory events. `samples`' cardinality is unaffected either way (it always equals the
  requested RANGE/TIME schedule's), so cross-engine/tolerance comparisons relying on that (see
  `test_cashkarp_tolerance_controls_adaptive_step_count`) still hold.
- `py_ballisticcalc/trajectory_data.py`: `HitResult.interpolate()`, `index_at_distance()`,
  `get_at_distance()`, and `get_at_time()` searched `self.trajectory` — the presentation table
  that projects events onto nearby scheduled samples — instead of `self.records`, the exact
  chronological stream. Since `trajectory` can omit an event-only row (folding its flag onto a
  neighboring sample instead), these lookups could silently miss or misattribute the point a
  caller asked for. Also: `interpolate()` raised `ValueError` for fewer than 3 bracketing
  points; it now raises `ArithmeticError` for consistency with its other failure paths, and
  additionally falls back to linear interpolation when exactly 2 points bracket the target
  (previously an unconditional raise).
- `py_ballisticcalc/trajectory_data.py`: `TrajectoryStep.at_x()` now assigns the exact queried
  downrange target to the result's `position.x` instead of re-deriving it from the
  bisection-converged Hermite sample (`TrajectoryStep.at_value`, which `record_step`'s
  RANGE-step sampling used directly before this). Invisible at Python's double precision
  (residual is far below any existing tolerance) — the same pattern in `tiny_bclibc`'s C port of
  this logic measurably missed an exact RANGE-step target once run in single precision (see
  `bclibc`'s CHANGELOG), so this keeps all three implementations (this one, bclibc's C++, and
  `tiny_bclibc`'s C99) consistent rather than relying on double precision to hide it here too.
- `py_ballisticcalc/engines/base_engine.py`: `BaseIntegrationEngine._zero_angle`'s convergence
  check inside its damped-Newton iteration loop compared `height_error_ft` against the
  hardcoded module-level `cZeroFindingAccuracy` constant (`5e-6` ft) instead of
  `self._config.cZeroFindingAccuracy` (already used correctly two lines above, for the initial
  `height_error_ft`, and after the loop, for the final success/failure check) — so a caller
  who configured a looser `cZeroFindingAccuracy` still had the loop itself hold out for `5e-6`
  ft every iteration. No effect under the default config (`5e-6` ft either way). Found while
  adding `TinyBclibcSingleIntegrationEngine` above: float32 cannot represent position to `5e-6`
  ft at typical zero distances, so `_zero_angle`'s primary method always exhausted its
  iteration budget and fell back to the ~10-50x more expensive guaranteed method
  (`_find_zero_angle`, which itself requires a `_find_max_range` golden-section search first)
  — fixing this bug (so the configured, looser tolerance is honored throughout) plus giving
  `TinyBclibcSingleIntegrationEngine` a `1e-3` ft default (matching `tiny_bclibc`'s own
  `TINY_BCLIBC_SINGLE_PRECISION` zero-finding tolerance) cut a `set_weapon_zero` call at 2000m
  from ~2.2s to ~36ms on the affected shot.

### CI
- `.github/workflows/pypi-publish.yml`: the `Cache cibuildwheel/pyodide toolchain` step (`actions/cache@v6` on `~/.cache/cibuildwheel`) is no longer Pyodide-only — it now runs for every `matrix.cibw_platform` except `linux` (macOS, Windows, Android also download interpreters/toolchains that `CIBW_CACHE_PATH` covers: CPython/PyPy/GraalPy installers, nuget packages, the Android NDK), keyed per `matrix.artifact_key` instead of one shared `cibw-pyodide-<runner.os>` key; Linux is excluded because manylinux/musllinux builds fetch their Docker base images via `docker pull`, which `CIBW_CACHE_PATH` does not cover. The "Build binary python package" step now also sets `CIBW_CACHE_PATH: ~/.cache/cibuildwheel` explicitly (kept in sync with the cache step's `path`) instead of relying on cibuildwheel's platform-specific default cache location
- `uv lock --upgrade` (both `uv.lock` and `py_ballisticcalc.exts/uv.lock`) — routine dependency bump surfaced by `pre-commit`'s `uv-lock`/`uv-lock-exts` hooks once the `bclibc` submodule was initialized locally (cython, ruff, scipy, scipy-stubs, filelock, dependency-groups, pymdown-extensions, pyzmq, vcs-versioning, appnope)

## [2.3.1] - 2026-07-06
[:simple-github: GitHub release][2.3.1]

### Added
- Native `py_ballisticcalc.exts` wheels for Android (`cp313-android_*`/`cp314-android_*`, `arm64_v8a`+`x86_64`) via a new `cibuildwheel[android]`-driven CI job — `.github/workflows/pypi-publish.yml`, `[tool.cibuildwheel.android]` in `py_ballisticcalc.exts/pyproject.toml` ([#339])
- Native `py_ballisticcalc.exts` wheels for Pyodide/WebAssembly (`cp313-pyodide_*`/`cp314-pyodide_*`, `wasm32`) via `cibuildwheel[pyodide]`, with its own `~/.cache/cibuildwheel` cache keyed on `pyproject.toml`'s hash — `[tool.cibuildwheel.pyodide]` in `py_ballisticcalc.exts/pyproject.toml`, `.github/workflows/pypi-publish.yml` ([#340]); confirmed against the actual `2.3.1b2` PyPI release: `cp313` built against Pyodide xbuildenv `0.29.4` (wheel tag `cp313-cp313-pyemscripten_2025_0_wasm32`), `cp314` against a newer, not-yet-stable xbuildenv (tag `cp314-cp314-pyemscripten_2026_0_wasm32`) — each Pyodide release pins one exact CPython+Emscripten ABI (see `setup.py` comment below), so a wheel only installs under the matching Pyodide version
- `examples/pyodide/index.html`: standalone, browser-only interactive REPL demoing `py_ballisticcalc`/`py_ballisticcalc.exts` running entirely client-side under Pyodide — no server, no install. Rebuilds the official [Pyodide `console.html`](https://github.com/pyodide/pyodide/blob/main/src/templates/console.html) terminal (jQuery Terminal + `pyodide.console.PyodideConsole`, top-level `await`, `Ctrl+C`, tab-completion) pinned to the Pyodide build matching the `cp313` wasm32 wheel above, then on load feeds a `.338LM`/300gr SMK example (`micropip.install(..., pre=True)` since `2.3.1b2` is a pre-release → `cythonized_rk4_engine` zero + 1000 m trajectory) into the live console as a normal, narrated transcript rather than running it silently, leaving `calc`/`shot`/`weapon`/`ammo`/`result` in scope for further exploration; four `<script src>` tags moved from `<head>` to the end of `<body>` so the loading spinner paints immediately instead of being blocked behind the Pyodide/jQuery Terminal downloads
- `docs/pyodide` (symlink to `examples/pyodide/`, `not_in_nav: pyodide/*` in `mkdocs.yml` to silence the resulting "omitted from nav" warning) and a new "Interactive Web REPL" nav entry linking straight to the raw `pyodide/index.html` page (deliberately not wrapped in a `.md` doc page or an `<iframe>`: an iframe embed of a full Pyodide runtime was noticeably laggy, and a raw asset is excluded from `sitemap.xml`, which keeps Material's `navigation.instant.preview` hover-card from trying to render it) — `mkdocs.yml`, `docs/index.md`, `README.md`
- `[![powered by pyodide]][Pyodide]` badge in `README.md`, alongside a new (previously unbadged) `[![powered by bclibc]][bclibc]` — both use a base64-embedded logo (bclibc: its own circular mark; pyodide: the white-on-transparent `logo-quadratic-dark.svg` from [pyodide/pyodide-artwork](https://github.com/pyodide/pyodide-artwork), chosen over the wordmark `logo-dark.svg`/`logo-light.svg` variants because shields.io badge logos need a roughly square aspect ratio) so the icon renders standalone without depending on an external stylesheet or the shields.io logo-service's own icon set

### Changed
- `py_ballisticcalc.exts/setup.py`: cross-compile target detection (`IS_EMSCRIPTEN`/`IS_ANDROID`/`IS_IOS`, via `sysconfig.get_platform()` rather than `platform.system()`, which reports the *host* OS under cross-compilation) now also disables the stable-ABI (`abi3`) build for Android and iOS, not just Emscripten — Android's Bionic `dlopen` requires every dependency to resolve to a literal `libpythonX.Y.so` at load time (no lazy glibc-style symbol resolution), so an `abi3` wheel only *looks* version-independent while actually hardcoding a dependency on one CPython point release; confirmed empirically (a `cp311-abi3-android` wheel built against a `cp313` Android crossenv failed to import on 3.14 with `library libpython3.13.so not found`); also adds an Emscripten-specific compiler-flags branch (`-std=c99`/`-std=c++11`, no `CC`/`CXX` override since `pyodide-build` already sets `emcc`/`em++`, no `-Wl,-strip-all` since `em++`'s linker wrapper doesn't reliably support it) ([#339])
- `.github/workflows/pypi-publish.yml` wheel-build matrix: every entry now carries a descriptive `name` (shown in the Actions UI as "Build wheels on ubuntu-latest / Pyodide WebAssembly" etc.), an `artifact_key` (upload-artifact names are now `dist-wheels-<key>` instead of `dist-<os>`, since Android/Pyodide/Linux-x64 all share `os: ubuntu-latest`), and an explicit `cibw_platform` (`--platform {% raw %}${{ matrix.cibw_platform || 'auto' }}{% endraw %}`, output moved from `./dist` to `./wheelhouse` to avoid colliding with the sdist job's `./dist`); macOS runners bumped `macos-15`/`macos-15-intel` → `macos-26`/`macos-26-intel` (also in `pytest-{rk4,cythonized-rk4,scipy}-engine.yml`, plus added to the `pytest-manual.yml` `workflow_dispatch` OS dropdown); `SETUPTOOLS_SCM_OVERRIDES` env var (and matching `CIBW_ENVIRONMENT_PASS` entry, needed for container-based builds like manylinux which don't otherwise inherit the host env) now sets `local_scheme = "no-local-version"` on push/TestPyPI runs, since PyPI/TestPyPI reject local version segments (`+g<hash>`) that build-only runs keep for traceability ([#339])
- `.github/dependabot.yml`: the two separate `uv` ecosystem blocks (root + `py_ballisticcalc.exts/`) merged into one block with `directories: ["/", "py_ballisticcalc.exts/"]`; the freed-up per-`py_ballisticcalc.exts` block repurposed to an `npm` ecosystem entry watching `py_ballisticcalc.exts/pyodide/` (the pyodide/emscripten cross-build toolchain pulls in node/npm dependencies) ([#340])
- `.gitignore`: `**/wheelhouse` (new `cibuildwheel` output dir, see above), `**/.pyodide_build`, `**/node_modules/` ([#340])
- `README.md`: `[![pyright]]` badge replaced by `[![Pre-commit]]` — pyright has run as a `.pre-commit-config.yaml` hook via the consolidated `pre-commit.yml` workflow since `2.3.0`, so the standalone `pyright.yml` badge/workflow link was already stale; engine-comparison table column widths realigned (padding only, no content change — had gone ragged after `2.3.0` added the `cythonized_verlet_engine` row without matching the other rows' width)

### CI
- `.github/workflows/pypi-publish.yml`: `Cache cibuildwheel/pyodide toolchain` step (`actions/cache@v6` on `~/.cache/cibuildwheel`) added for the Pyodide job only — the Pyodide xbuildenv/Emscripten SDK download is the slowest part of that build and doesn't change between runs unless `py_ballisticcalc.exts/pyproject.toml` does ([#340])

## [2.3.0] - 2026-07-24
[:simple-github: GitHub release][2.3.0]

### Added
- `cythonized_verlet_engine` (`py_ballisticcalc_exts.CythonizedVelocityVerletIntegrationEngine`): compiled counterpart to the existing pure-Python `verlet_engine`, wired up the same way as `cythonized_rk4_engine`/`cythonized_euler_engine` (`velocity_verlet_engine.pxd`/`.pyx`/`.pyi`, `setup.py` source/dependency registration, `py_ballisticcalc_exts/__init__.py` export, `[project.entry-points.py_ballisticcalc]` in `py_ballisticcalc.exts/pyproject.toml`) against bclibc's `BCLIBC_integrateVELOCITY_VERLET` (`include/bclibc/velocity_verlet.hpp`, released in bclibc [`v1.1.7`](https://github.com/ballistics-lab/bclibc/releases/tag/v1.1.7)); produces identical trajectories to `verlet_engine` bit-for-bit on a standard test shot and passes the full `pytest` suite (373 passed, 2 skipped) and `py_ballisticcalc.exts/tests`; benchmarked at 100x (Trajectory) / 157x (Find Zero) faster than `rk4_engine` — added to the engine comparison table in `README.md`/`docs/concepts/engines.md`
- `.github/workflows/pytest-cythonized-verlet-engine.yml`: minimal-matrix CI (`ubuntu-latest` × `3.11`, push + PR) for `cythonized_verlet_engine`, mirroring `pytest-cythonized-euler-engine.yml` — no full cross-OS/version matrix since it shares its integration/data-structure core with `cythonized_rk4_engine` (which keeps the full matrix); `README.md` badge added
- `.github/workflows/pytest-manual.yml`: added `cythonized_verlet_engine` to the `engine_name` `workflow_dispatch` dropdown (its `options:` list is hand-maintained, unlike `pytest-reusable.yml`/`ci-helpers.sh`, which key off a generic `cythonized_*` prefix and needed no change); `.github/workflows/coverage.yml` also needed no change — it discovers engines dynamically via `Calculator.iter_engines()`, confirmed by simulating its `discover-engines`/`test` steps locally (engine listed, `--extra exts` installed, coverage run passes)

### Changed
- bclibc submodule bumped to [`v1.1.7`](https://github.com/ballistics-lab/bclibc/releases/tag/v1.1.7) — adds the `velocity_verlet` integration method (see Added)
- `.pylintrc` (643 lines, essentially unmodified `pylint --generate-rcfile` output) replaced by `[tool.pylint.main]`/`[tool.pylint.design]`/`[tool.pylint."messages control"]` in `pyproject.toml`; diffed against a freshly generated default rcfile of the same pylint version to isolate the actual overrides (`fail-under=9.0` vs default `9.5`, `max-positional-arguments=6` vs default `5`, `ignore`, `py-version`, and the `disable=` list — which, despite reading like `--generate-rcfile`'s own suggested defaults, is *not* applied unless present in a config file: without it, pylint's score on `py_ballisticcalc` drops from 9.57/10 to 7.89/10); verified byte-for-byte equivalent pylint findings/score before deleting `.pylintrc`
- `[tool.ruff] extend-exclude` (`pyproject.toml`) gained `py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc` — `ruff check --fix` was reaching into the vendored bclibc submodule (a separate upstream repo) and rewriting its typing (`Optional[X]` → `X | None`, etc.); confirmed `[tool.ruff.lint].exclude` does *not* control file discovery the way top-level `exclude`/`extend-exclude` do (ruff still walked and linted files under it when only `lint.exclude` was set), so the fix went into the shared top-level exclude instead
- `py_ballisticcalc/interface.py`: `from py_ballisticcalc import RK4IntegrationEngine` → `from py_ballisticcalc.engines import RK4IntegrationEngine` — the former was a real (if currently-working) circular import: `py_ballisticcalc/__init__.py` imports `interface.py`, which imported back from the partially-initialized `py_ballisticcalc` package itself; it only worked because `__init__.py` happens to import `.engines` before `.interface`, leaving the whole package's importability fragile to any future reordering of that file (caught by pylint's `cyclic-import`, which `ruff`'s `PL*` rule subset does not implement)
- `py_ballisticcalc/engines/base_engine.py`, `rk4.py`, `engines/scipy_engine.py`, `unit.py`, `vector.py`, `generics/engine.py`, `interpolation.py`, `constants.py`, `drag_tables.py`, and several `py_ballisticcalc.exts` scripts: broad `ruff check --fix` cleanup — typing modernization (`Optional[X]`/`List[X]`/`Dict[X]` → `X | None`/`list[X]`/`dict[X]`), `set()`/`tuple()` literal rewrites, `.keys()` removal, nested-`if` merges (only where no attached `elif` would change semantics — a first attempt at merging `base_engine.py`'s `ZERO_UP`/`ZERO_DOWN` crossing-detection nesting *did* change semantics and was reverted after it broke `TestTrajectoryDataFilter.test_zero_up_then_zero_down_ordering`), `yield`-loop → `yield from`, `%`-format → f-string, `ClassVar` annotations on `Unit`'s per-subclass `_conversion_factors` (`RUF012`), and shebang scripts (`cythonization-report.py`, `setup.py`, `uconv.py`) marked executable (`EXE001`); a handful of findings were suppressed with `# noqa` + rationale instead of "fixed" where the suggestion didn't match the code's actual intent: `PreferredUnitsMeta.__repr__`'s `getattr(cls, "__dataclass_fields__")` (pyright can't see the attribute `@dataclass` injects onto the metaclass at runtime — ruff's own `--fix` had silently rewritten this to direct attribute access, which is what broke `pyright`), `Vector.__iadd__`/`__isub__` (immutable `NamedTuple`: genuinely returns a new instance, not `self`, contra `PYI034`), `ConfigT` in `generics/engine.py` (public name re-exported from `generics/__init__.py`, contra `PLC0105`'s naming convention), and both `__all__` sequences in `constants.py`/`interpolation.py` (deliberately grouped by category with comments, contra `RUF022`'s alphabetical sort)
- `py_ballisticcalc/engines/rk4.py`, `engines/scipy_engine.py`: closures created inside per-iteration loops (`acceleration()` in RK4, `x_minus_target()` in SciPy's root-finding) now bind their loop-scoped variable (`k_m`, `x_target`) as a default argument instead of relying on the closure — both were already correct at runtime (fully invoked before the next iteration reassigns the variable) but tripped `B023`; the default-argument form makes that safety explicit rather than incidental

### Fixed
- `.github/workflows/pre-commit.yml`: checkout step was missing `submodules: recursive`, so the consolidated pre-commit workflow (see CI) failed its `uv-sync` hook on every run — `py_ballisticcalc.exts`' Cython build needs `bclibc`'s vendored C++ sources, which a non-recursive checkout never fetches

### Removed
- `.pylintrc` — migrated into `pyproject.toml` (see Changed)

### CI
- `.github/workflows/pyright.yml`, `ruff.yml`, `pylint.yml` removed; all three now run as `.pre-commit-config.yaml` hooks (`uv-pyright`, `uv-ruff-check`, `uv-ruff-format`, `uv-pylint`) via the existing `.github/workflows/pre-commit.yml` (`pre-commit run --all-files`), instead of three separate workflows each reinstalling the project
- `.pre-commit-config.yaml`: `uv-pylint` hook scoped to `py_ballisticcalc` only (`args: [..., "py_ballisticcalc"]`, `pass_filenames: false`) instead of linting whatever `.py`/`.pyi` files changed anywhere in the repo with no path filter — the old form ran pylint against `py_ballisticcalc.exts`/`tests`/scripts that were never in its scope, always failing the `fail-under=9.0` gate locally (score dropped to 8.71) even for clean `py_ballisticcalc`-only changes
- `.pre-commit-config.yaml`: added `uv-lock-exts` hook (`uv lock --upgrade --project py_ballisticcalc.exts`), mirroring the existing `uv-lock` hook for the main package's `uv.lock`

## [2.3.0rc2] - 2026-07-21
[:simple-github: GitHub release][2.3.0rc2]

### Changed
- bclibc submodule bumped to [`v1.1.5`](https://github.com/ballistics-lab/bclibc) — `BCLIBC_BaseTrajSeq::get_at()` (`src/traj_data.cpp`) silently extrapolated instead of raising when `key_value` was outside the trajectory's range, since `bisect_center_idx_buf()`/`find_target_index()` clamp their bracket index to `[1, n-2]` regardless of how far `key_value` falls outside the sequence, and `interpolate_at()` only ever validated the *index*, never the *value*; `get_at()` now checks `key_value` against `[min(buffer[0][key], buffer[n-1][key]), max(...)]` (± a `1e-9` epsilon) before searching and throws `std::out_of_range` (surfaces as Python `IndexError`) if it falls outside ([bclibc#19](https://github.com/ballistics-lab/bclibc/issues/19)); also fixes a broken artifact-path check in `pre-commit-check.sh` and adds a CTest-based C++ unit test target — surfaced while investigating [#305](https://github.com/o-murphy/py-ballisticcalc/issues/305) below

### Fixed
- `HitResult.get_at()` (`trajectory_data.py`): raised `ArithmeticError: Trajectory does not reach ...` when the requested value was a floating-point epsilon beyond an existing trajectory point (e.g. from meter→inch conversion artifacts) instead of returning that point; the forward-search loop's bracket condition (`curr_val < key_value <= next_val`) excludes any `key_value` past the bracket it can find, so `target_idx` stayed `-1` and the error was raised before the `epsilon` check could ever run, regardless of how large `epsilon` was passed — this affected not just the first/last trajectory points but also interior local extrema (e.g. the trajectory apex) for non-monotonic attributes like height, since an extremum epsilon-overshoot falls outside every bracket the same way an endpoint epsilon-overshoot does; fix: on `target_idx == -1`, scan the whole trajectory for its closest point by key-attribute value (`min(traj, key=...)`) and return it if within `epsilon` — only reached on this error-fallback path, so the O(n) scan has no cost on the normal path — resolves [#305](https://github.com/o-murphy/py-ballisticcalc/issues/305); pure-Python fix — `py_ballisticcalc_exts`' internal `CythonizedBaseTrajSeq.get_at()` (bclibc) uses a different binary-search-and-always-interpolate algorithm not affected by this specific bug, but investigating it surfaced the opposite problem there (see bclibc submodule bump to `v1.1.5` above)

### Tests
- `TestIssue305` added to `tests/test_issues.py` — regression tests for `HitResult.get_at()`: a value a float-epsilon past the last trajectory point resolves to that last point, a value a float-epsilon before the first point resolves to the first point, a value a float-epsilon past an interior local extremum (trajectory apex) resolves to that extremum, and a value genuinely far out of range still correctly raises `ArithmeticError`
- `py_ballisticcalc.exts/tests/test_get_at_functions.py`: added `CythonizedBaseTrajSeq.get_at()` regression tests mirroring `TestIssue305` for the Cython/bclibc path — epsilon past/before the first and last points still resolve to those points, and values genuinely far out of range now raise `IndexError` per the bclibc `v1.1.5` fix

### CI
- `.github/workflows/coverage.yml`: added top-level `concurrency: {group: "{% raw %}${{ github.workflow }}{% endraw %}-{% raw %}${{ github.ref }}{% endraw %}", cancel-in-progress: true}`, matching every other workflow in the repo — a new push/PR update now cancels the previous in-flight coverage run on the same ref instead of both running to completion
- `.github/workflows/coverage.yml`: `discover-engines` and `merge` jobs now skip when `github.actor == 'dependabot[bot]'` (`test` skips too, transitively, via its `needs: discover-engines`) — dependency-bump PRs don't need a fresh full-matrix coverage run, and `merge`'s existing `if: {% raw %}${{ !cancelled() }}{% endraw %}` would otherwise still have attempted to run (and fail, with no coverage data to combine) even with `discover-engines`/`test` skipped, since a skipped job isn't a cancelled one
- `pytest-euler-engine.yml`, `pytest-verlet-engine.yml`, `pytest-cythonized-euler-engine.yml`: `test_full_matrix` job (6-OS × `3.11`/`3.14`/`3.14t` matrix, PR-only) removed; `test_minimal_matrix` (`ubuntu-latest` × `3.11` only) now runs unconditionally on both `push` and `pull_request` instead of push-only — these three engines share their integration/data-structure code with `rk4_engine`/`cythonized_rk4_engine` (which keep the full cross-OS/version matrix), differing only in integration formula, so cross-platform/cross-version testing of that shared core would just be duplicated CI cost; the minimal matrix still catches regressions specific to each engine's own logic

## [2.3.0rc1] - 2026-07-20
[:simple-github: GitHub release][2.3.0rc1]

### Fixed
- CHANGELOG.md: the `v2.3.0b5` Codecov entry's `if: {% raw %}${{ !cancelled() }}{% endraw %}` GitHub Actions expression wasn't escaped for Jinja, so mkdocs/`pymdown-extensions` tried to evaluate it as a template expression when rendering the docs site; wrapped in `{% raw %}...{% endraw %}`

## [2.3.0b5] - 2026-07-20
[:simple-github: GitHub release][2.3.0b5]

### Added
- Codecov integration: `.github/workflows/coverage.yml` rewritten as a 3-job pipeline — `discover-engines` (lists engines via `Calculator.iter_engines()`), `test` (matrix over discovered engines, each writing an isolated `.coverage.<engine>` data file), `merge` (`coverage combine`/`xml`/`html`, then `codecov/codecov-action@v7` upload); `merge` runs even if one engine's tests fail (`if: {% raw %}${{ !cancelled() }}{% endraw %}`) so coverage is still reported
- `CODECOV_TOKEN` repository secret added; README `[coverage]` badge now links to the live codecov.io report instead of the local `coverage.svg`

### Changed
- `_EngineLoader` (`interface.py`): `_get_entries_by_group()` and new `_load_by_name()` wrapped in `functools.cache` — `entry_points().select(...)` was re-scanning all installed distributions on every string-keyed `Calculator(engine="...")` construction (~4.4ms/call); now cached per-process (~0.0085ms/call on repeat calls, ~500x) — mainly benefits code that repeatedly loads an engine by name, e.g. the class-scoped `loaded_engine_instance` pytest fixture and `Calculator.__setstate__` on unpickle
- Dependencies update to fix CVEs

### Fixed
- `ScipyIntegrationEngine` (`engines/scipy_engine.py`): 12 pyright `reportPossiblyUnboundVariable` findings on `np`/`root_scalar`/`minimize_scalar`/`solve_ivp` — these are optional third-party imports (`try`/`except ImportError`), but every use is only reachable after `SciPyIntegrationEngine.__init__` has already verified `_HAS_NUMPY`/`_HAS_SCIPY`, an invariant the type checker can't see across function boundaries; fixed by also importing them unconditionally under `if TYPE_CHECKING:` (never executed at runtime, only informs the type checker that the names are bound) — no runtime behavior change
- `ScipyWindSock.__init__` (`engines/scipy_engine.py`): `winds` parameter was typed `Wind | Sequence[Wind | None]`, which (a) allowed `None` *items* inside the sequence even though nothing ever produces or handles those, and (b) didn't even include bare `None` as a valid top-level value despite the method explicitly handling `winds is None`; corrected to `Wind | Sequence[Wind] | None`, matching the real caller (`props.winds`, typed `Sequence[Wind]`) and the existing `None`-handling code
- `ColoredFormatter.__init__` (`logger.py`): `style` parameter had no type annotation, so pyright widened it to `str` and flagged the `super().__init__()` call as incompatible with `logging.Formatter`'s `Literal['%', '{', '$']`; annotated as `Literal["%", "{", "$"] = "%"`
- `GenericDimension.from_raw` (`unit.py:840`): parameter was named `unit`, while `Temperature.from_raw`'s override (`unit.py:1242`) and the `GenericDimensionProtocol` declaration both use `units`; pyright flagged the override as LSP-incompatible (`reportIncompatibleMethodOverride`); renamed the base method's parameter to `units` to match
- `VelocityVerletIntegrationEngine._integrate` (`engines/velocity_verlet.py`): `data_filter.finalize()` was called with no argument, defaulting `termination_reason` to `None` and silently no-opping (unlike `rk4.py`/`euler.py`, which pass `termination_reason` through); on any `RangeError` path (`MaximumDropReached`, `MinimumAltitudeReached`, incomplete/vertical shots) the real final trajectory point was never appended, so `HitResult.trajectory[-1]` stayed pinned at the muzzle point (`time=0.0`); fixed by passing `termination_reason` into `finalize()`, matching the other engines

### Removed
- `coverage.svg` (root) — was only ever regenerated by a commented-out `coverage-badge` step; the README `[coverage]` badge now points at codecov.io instead
- Orphaned unused `[coverage]` reference definition (pointing at a non-`raw.githubusercontent.com`, already-broken `coverage.svg` URL) removed from `py_ballisticcalc.exts/README.md`

### CI
- Type checker swapped from `mypy` to `pyright`, recommended by [Serhiy Yevtushenko](https://github.com/serhiy-yevtushenko): `[tool.mypy]` → `[tool.pyright]` in `pyproject.toml` (`include = ["py_ballisticcalc"]`); `mypy>=2.3.0` → `pyright>=1.1.411` in both dev dependency groups; `.pre-commit-config.yaml` `uv-mypy` hook → `uv-pyright`; `.github/workflows/mypy.yml` renamed to `pyright.yml`; `docs/contributing.md` command updated; stale `.mypy_cache/` entries removed from both `.gitignore` files; `.pylintrc`'s `spelling-ignore-comment-directives` `mypy:` → `pyright:`; `# Make mypy happy` comments in `base_engine.py`/`scipy_engine.py` reworded generically. `reportUnsupportedDunderAll` disabled in `[tool.pyright]` — `__init__.py`/`drag_tables.py` build `__all__` dynamically from `globals()`/a generated list by design, which pyright can't statically verify
- `.pre-commit-config.yaml`: `astral-sh/uv-pre-commit`'s pinned `uv-lock` hook (`rev: 0.11.29`) replaced with a local `language: system` hook running `uv lock --check` directly, placed right before `uv-sync` — avoids a second, independently-pinned `uv` version diverging from whatever `uv` is actually used to run the rest of the hooks and CI
- `.github/workflows/pytest-verlet-engine.yml` added — `verlet_engine` had no dedicated pytest-*-engine.yml (only `coverage.yml` exercised it); new file mirrors the euler/rk4/scipy pattern (full matrix on `pull_request`, minimal matrix on `push`, `fail-fast: false`)
- `.github/workflows/pytest-manual.yml`: `verlet_engine` added to the `engine_name` choice-input options
- `.github/workflows/pytest-reusable.yml`: `astral-sh/setup-uv` now sets `enable-cache: true` with an explicit `cache-dependency-glob` covering `py_ballisticcalc.exts/**` and `.gitmodules` (not just `uv.lock`/`pyproject.toml`) — a cache hit now skips rebuilding the Cython extension entirely when its source tree is unchanged from a prior run, e.g. across `cythonized_euler_engine`/`cythonized_rk4_engine` legs on the same runner or on job re-runs/retries
- `test_full_matrix`/`test_minimal_matrix` job `name:` shortened to `Full`/`Minimal` across `pytest-{euler,rk4,scipy,verlet}-engine.yml` and `pytest-cythonized-{euler,rk4}-engine.yml`; the two cythonized files' `test_minimal_matrix` previously had no explicit `name:` at all
- `.gitignore`: `.coverage` glob widened to `.coverage*` and `**/coverage.xml` added, to also ignore per-engine coverage data files (`.coverage.<engine>`) and generated XML reports from the new `coverage.yml`

## [2.3.0b4] - 2026-06-25
[:simple-github: GitHub release][2.3.0b4]

### Changed
- bclibc submodule reference updated from [`v1.1.2`](https://github.com/ballistics-lab/bclibc) to [`v1.1.4`](https://github.com/ballistics-lab/bclibc) — no additional wrapper-consolidation work of its own; picks up bclibc's interim `v1.1.3` fix (Ridder's-method `f_next` ordering, see `v2.3.0b3` below) plus further upstream `v1.1.4` changes

## [2.3.0b3] - 2026-06-22
[:simple-github: GitHub release][2.3.0b3]

### Changed
- `py_ballisticcalc.exts` (`bind.pyx`): `BCLIBC_ShotProps_from_pyobject` is now a thin field mapper — fills `BCLIBC_Shot` with natural-unit values and delegates all physics/unit conversions to `BCLIBC_Shot::to_shot_props()` in C++ (cant cos/sin, CIPM-2007 atmosphere, Coriolis trig, PCHIP drag curve, wind sock assembly); Step 2 of bclibc-wrapper-consolidation
- `py_ballisticcalc.exts` (`base_types.pxd`): added `BCLIBC_Shot` cppclass declaration
- `py_ballisticcalc.exts` (`base_types.pxd`): `BCLIBC_Coriolis` cppclass extended with `@staticmethod from_lat_az(lat_deg, muzzle_velocity_fps, az_deg)`
- `py_ballisticcalc.exts` (`base_types.pxd`): `BCLIBC_Atmosphere` cppclass extended with `@staticmethod from_conditions(t_c, p_hpa, alt_ft, humidity)`
- `py_ballisticcalc.exts` (`bind.pyx`): added `BCLIBC_Coriolis_from_lat_az` and `BCLIBC_Atmosphere_from_conditions` Cython helpers (available for callers that hold Python domain objects directly; `_from_pyobject` variants retained for the same reason)
- bclibc submodule bumped to [`v1.1.2`](https://github.com/ballistics-lab/bclibc) — adds `BCLIBC_Shot` / `to_shot_props()`, `BCLIBC_Coriolis::from_lat_az()`, `BCLIBC_Atmosphere::from_conditions()` (Steps 1–2); renames all `BC*` struct/enum types in `bclibc_ffi.h` to `BCLIBCFFI_*` and adds `BCLIBCFFI_*_shot()` entry points in the C FFI layer (Step 3a, breaking for C FFI consumers); no effect on Cython path (`base_types.hpp` `BCLIBC_*` types are unchanged)

### Fixed
- `_find_zero_angle()` (`base_engine.py`): units mismatch in Ridder's bracket-convergence checks — `cZeroFindingAccuracy` is a **height tolerance in feet** but was also used as an **angle tolerance in radians** (`if abs(next_angle - mid_angle) < cZeroFindingAccuracy`); with the default `5e-6` the angle bracket had to narrow to `5e-6 rad ≈ 0.0003°`, causing oscillation and exhausting `cMaxIterations` on certain high-elevation geometries; additionally, the Python implementation lacked explicit height-error checks (`|f_mid|`, `|f_next|`) that the C++ version has, so convergence was never declared even when the bullet already crossed the sight line within tolerance; fix: introduce a separate `angle_tol = 1e-7 rad` for bracket convergence, add `|f_mid| < cZeroFindingAccuracy` and `|f_next| < cZeroFindingAccuracy` height checks, and evaluate `f_next` before the angle-step exit — resolves [#204](https://github.com/o-murphy/py-ballisticcalc/issues/204)
- bclibc submodule bumped to `v1.1.3` — `src/engine.cpp`, `tiny_bclibc/include/tiny_bclibc/engine.h`: same Ridder's-method fix — `f_next` now evaluated before the `angle_tol` / `kRiddersAngleTol` check in both the C++ and C implementations
- `CythonizedBaseTrajData.__str__` unpacked `(name, value)` from an iterator that yields scalar values — raised `ValueError` on any call
- `Vacuum.__init__` (`conditions.py`): `Atmo.__init__` uses `pressure or standard_pressure(...)` so passing `pressure=0` (falsy) stores `_p0 = 1013.25 hPa` instead of `0`; `Vacuum.__init__` corrected `_pressure` and `_density_ratio` but not `_p0`; any C++ wrapper reading `_p0` directly (e.g. Dart FFI, WASM) would receive 1013.25 hPa for vacuum; fix: explicitly set `self._p0 = 0.0` in `Vacuum.__init__` after `super().__init__()`
- `BCLIBC_ShotProps_from_pyobject` (`bind.pyx`): `shot_info.winds` was accessed twice (once for `len()`, once for the for-loop); `Shot.winds` returns `tuple(self._winds)` — a new tuple on every call; under free-threading a concurrent mutation of `_winds` between the two accesses could make `wind_count > winds_vec.size()`, causing an out-of-bounds read in `BCLIBC_Shot::to_shot_props()`; fix: cache `winds_py = shot_info.winds` once before both uses
- `BCLIBC_ShotProps_from_pyobject` (`bind.pyx`): `shot_info.ammo`, `.ammo.dm`, `.atmo`, and `.weapon` were traversed multiple times each without being cached in `cdef object` locals, violating the function's own documented invariant ("Cython may forget to add DECREF") — each chain traversal creates a temporary reference that Cython may not release on exception paths; fix: cache all intermediates in named `cdef object` locals at the top of the function

### Tests
- `TestIssue204` added to `tests/test_issues.py` — parametrized regression suite covering 9 high-elevation target points from issue #204 that previously raised `ZeroFindingError`; tests both `zero_angle()` (iterative + Ridder's fallback) and `find_zero_angle()` (direct Ridder's); all engines run with `cStepMultiplier=5.0` to keep runtime reasonable on high-elevation trajectories

### CI
- `py_ballisticcalc.exts/pyproject.toml`: removed `enable = ["cpython-freethreading"]` — no longer a valid enable group in cibuildwheel 4.x; removed `cp313t-*` from `build` selectors — Python 3.13t is no longer available in cibuildwheel 4.1.0 (left preview stage); final selectors: `cp311-* cp314t-*`
- `test_full_matrix` in `pytest-cythonized-rk4-engine.yml` and `pytest-cythonized-euler-engine.yml`: changed `fail-fast` from `false` to `true` — stops the 24-job matrix on the first failure instead of running all jobs to completion
- `cibuildwheel` build selectors: `cp311-* cp313t-* cp314t-*`; `cp313t-*` requires `enable = ["cpython-freethreading"]` in cibuildwheel 3.4 (flag is deprecated but `cp313t` is silently skipped without it)
- Cythonized engine test full matrix: `3.11, 3.14` (abi3 boundary versions) + `3.13t, 3.14t` (distinct free-threaded ABIs); `3.12`, `3.13` removed — abi3 binary is identical across standard CPython versions
- `pypi-publish.yml`: extracted `build-sdist` job — pure Python wheel and exts sdist built once on `ubuntu-latest`; removed from per-OS `build` matrix jobs to eliminate 5× redundant platform-independent builds

## [2.3.0b2] - 2026-05-13
[:simple-github: GitHub release][2.3.0b2]

### Changed
- `BaseEngineConfigDict` fields changed from `T | None` to `T` — `total=False` already provides optionality; explicit `None` values no longer accepted
- `with_no_minimum_velocity` and `with_max_drop_zero` decorators typed with `ParamSpec`, `Concatenate`, and `functools.wraps` — decorated methods now preserve their full signatures for static type checkers
- `TrajectoryDataFilter.records` class-level mutable default `= []` removed; annotation-only declaration left, instance assigned in `__init__`
- `isinstance(x, (A, B))` replaced with `isinstance(x, A | B)` union syntax (PEP 604) across `unit.py`, `vector.py`, `munition.py`, `trajectory_data.py`, `engines/scipy_engine.py`
- Implicit type aliases annotated with `TypeAlias` in `interface.py`, `munition.py`, `interpolation.py`, `trajectory_data.py`
- `typing.Self` merged into existing `from typing import (...)` block in `unit.py`; duplicate `from typing import` blocks merged in `trajectory_data.py` and `generics/engine.py`
- `importlib.metadata` compatibility shim removed from `_EngineLoader._get_entries_by_group` — `entry_points().select()` used directly (available since Python 3.9)
- `from __future__ import annotations` removed from `engines/base_engine.py`, `visualize/plot.py`, and `shot.py`; `shot.ShotProps.from_shot` return type updated to `Self`
- `typing.Self` moved from `typing_extensions` to stdlib `typing` in `interface.py`
- `tomllib` imported directly from stdlib (Python 3.11+), version guard removed
- `Callable` moved from `typing` to `collections.abc` in `helpers.py`

### Removed
- Python 3.10 support EOL - removed all references to Python 3.10, updated CI and dependencies

### CI
- `py_ballisticcalc.exts` wheels now target the Python stable ABI (`cp311-abi3-*`): one binary per platform/architecture is compatible with CPython 3.11 and all later standard releases; free-threaded Python 3.13t / 3.14t is built as separate version-specific wheels
- `cibuildwheel` reduced to `cp311-* cp314t-*` — eliminates redundant per-interpreter builds for standard CPython; `cp313t-*` dropped (deprecated in cibuildwheel 3.4, removed in next minor), `cp314t-*` requires no `enable` flag
- Cythonized engine test full matrix reduced from 6 to 3 Python versions (`3.11, 3.14, 3.14t`); `3.12`, `3.13`, `3.13t` removed — abi3 binary is identical across standard versions, boundary versions provide sufficient coverage
- `CIBW_ENVIRONMENT_PASS: SETUPTOOLS_SCM_PRETEND_VERSION` added to the publish workflow — previously the version override was not forwarded into `cibuildwheel` build containers, causing `+gHASH` local version suffixes that PyPI rejects
- `uv audit` pre-commit hook added — checks for known vulnerabilities in locked dependencies before each commit
- `uv lock --upgrade` — all dev/docs dependencies updated; resolves 18 Dependabot security alerts (Pillow, urllib3, tornado, CairoSVG, fonttools, requests, virtualenv, Pygments, pymdown-extensions)
- `pypi-publish.yml` trigger changed from `release: published` to `push: tags: v*`; `create-release` job added — generates and creates a draft GitHub Release automatically on tag push
- `.github/actions/gen_release_notes/` — new composite action with a Python script that builds formatted release notes from `CHANGELOG.md`; supports optional `> intro` and `### Upgrade Notes` sections; auto-collects contributors via `git log`
- `.mailmap` added — normalizes git author aliases to GitHub usernames for consistent contributor attribution

## [2.2.10] - 2026-04-30
[:simple-github: GitHub release][2.2.10]

### Changed
- bclibc C++ engine is now a git submodule (previously vendored sources)
- bump bclibc to v1.0.4
- `BCLIBC_Curve_fromPylist` in `py_bind.cpp` now delegates to `build_pchip_curve_from_arrays` — the universal PCHIP builder extracted into `base_types.hpp`/`base_types.cpp`; eliminates code duplication between the Cython and FFI paths
- `BCLIBCFFI_CATCH` macro replaced with `ffi_call<F>` template — same catch logic, no hidden `return`, full `catch(...)` coverage for non-std exceptions across the FFI boundary
- `try_get_exact` signature changed from `void` (exception-as-control-flow) to `bool`; call sites in `get_at` converted from `try/catch` blocks to plain `if` checks — removes overhead on the hot interpolation path

### Fixed
- bclibc: undefined behavior in `find_zero_angle` — missing `return` after Ridder's loop
- bclibc: `~BCLIBC_TrajectoryDataFilter` destructor no longer throws (wrapped in `try/catch`)
- bclibc: `BCLIBC_BaseTrajData::operator[]` bounds check used wrong constant and `>` instead of `>=`
- bclibc: `BCLIBC_TrajectoryData::interpolate` bounds check used `>` instead of `>=`, allowing `FLAG` key
- bclibc: `try_get_exact` refactored from exception-as-control-flow to returning `bool`
- bclibc: memory leak in `BCLIBCFFI_integrate` when `toC` loop throws after `malloc`
- bclibc: infinite loop guard added for `calc_step <= 0` in Euler and RK4 integrators
- bclibc: `BCLIBC_ShotProps` constructor no longer propagates `domain_error` from stability coefficient calculation
- bclibc: `BCLIBCFFI_CATCH` macro replaced with type-safe `ffi_call<F>` template (adds `catch(...)` for non-std exceptions)

## [2.2.9] - 2026-03-16
[:simple-github: GitHub release][2.2.9]

### Changed
- Updated CI dependencies versions
- Updated a list of package dependencies in pyproject.toml

### Fixed
- Fixed `Unit.Joule` conversion factor in `Energy` class returning incorrect foot-pounds to Joules values.
- Types annotations codestyle fix
- Security fix for vulnerability described at (https://github.com/o-murphy/py-ballisticcalc/security/dependabot/1)

## [2.2.8] - 2026-01-26
[:simple-github: GitHub release][2.2.8]

### Added
- `Calculator` now can be used as a context manager

### Changed
- `Calculator` - improved initialisation and type annotations
- engines `__init__` signature adjusted for consistency

### Fixed
- Type annotations fix in `unit.py`
- `EngineProtocol` - type annotations fix
- `Calculator` - type annotations fix
- Type annotations modernized to Python 3.10+ style (PEP 604, PEP 585)
  - `Optional[X]` → `X | None`
  - `Union[X, Y]` → `X | Y`
  - `List[X]` → `list[X]`, `Dict[K, V]` → `dict[K, V]`, `Tuple[X, Y]` → `tuple[X, Y]`
  - Removed unused typing imports
  - Updated .pyi stub files for Cython extensions
  - Added type guards in `uconv.py`

## [2.2.7] - 2025-12-26
[:simple-github: GitHub release][2.2.7]

### Changed
- C++ headers includes refactoring
- Redundant Null Pointer Check Removal in `BCLIBC_Coriolis`
- Better `BCLIBC_WindSock` initialization in Cython/C++
- `BCLIBC_WindSock_from_pylist` renamed to `BCLIBC_WindSock_from_pytuple`
- C++ to Python Exception bridge improved, avoids multiple rethrows, uses `dynamic_cast`
- C++ to Python Exception bridge `many_exception_handler` renamed to `exception_dispatch`
- `BCLIBC_BaseTrajData::get_key_val` replaced with `BCLIBC_BaseTrajData::operator[]` 
- `BCLIBC_BaseTrajSeq::get_key_val` replaced with `BCLIBC_BaseTrajSeq::operator[]` 
- `BCLIBC_TrajectoryData::get_key_val` replaced with `BCLIBC_TrajectoryData::operator[]` 

### Fix
- Docstrings fix according to [Issue #299](https://github.com/o-murphy/py-ballisticcalc/pull/299)

## [2.2.6.post1] - 2025-12-14
[:simple-github: GitHub release][2.2.6.post1]

### Changed
- Removed unnecessary atmosphere precalculation in C++ rk4 integrator
- Removed unnecessary 'edited' trigger from pypi-publish.yml

## [2.2.6] – 2025-12-13
[:simple-github: GitHub release][2.2.6]

### Changed 
- Optimized C++ based RK4 integrator performance
- V3dT uses square check instead of sqrt for magnitude calculation for performance 

### Fixed
- C++ based TrajectoryDataFilter initialization fix

### Compatibility
- Fully compatible with v2.2.3 (no breaking changes).
- Rebuilding wheels is recommended for distributors.

## [2.2.5] – 2025-12-11
[:simple-github: GitHub release][2.2.5]

### Added
- Improvements in integrator termination control and integration helpers.
- CI/CD enhancements including reusable wheel builds and better version extraction.

### Changed
- Major internal migration to a C++-centric engine design.
- Simplified Cython bindings and improved Python-level ergonomics.
- Significant memory usage optimizations.
- Thread-safety improvements in core engine components.
- Updated documentation, README, and contributor guidelines.

### Fixed
- Eliminated redundant copying in internal data pipelines.
- Fixed documentation build issues.
- Numerous bug fixes across the engine, wrappers, and integration logic.

### Compatibility
- Fully compatible with v2.2.3 (no breaking changes).
- Rebuilding wheels is recommended for distributors.
- Thread-safety improvements may positively affect multi-threaded usage.


## [2.2.5rc3] - 2025-12-10
[:simple-github: GitHub release][2.2.5rc3]

### Changed
- Refactoring and features improvements
- Attempted to use std::function for better functionality

### Fixed
- Made type annotations better and more accurate

## [2.2.5rc2] - 2025-12-02
[:simple-github: GitHub release][2.2.5rc2]

### Added
- C++-level `GenericTerminator` for better control
- `CythonizedBaseIntegrationEngine.integrate_raw_at` method to integrate by key_attribute and target_value
- Thread safety with `std::recursive_mutex` for `BCLIBC_Engine` fields

### Changed
- Control integrator termination from external handlers
- Much more safe `BCLIBC_EssentialTerminators` usage
- Refactored termination control from outer `BCLIBC_EssentialTerminators`

### Fixed
- C++ memory usage optimization

## [2.2.5rc1] - 2025-11-28
[:simple-github: GitHub release][2.2.5rc1]

### Added
- Automatic version detection during build/install using `setuptools-scm`
- RAII initialization to prevent memory leaks in trajectory filters
- Dense output support for trajectory handling

### Changed
- **Major refactor**: Fully ported ballistic engine from C/Cython to C++ with thin Cython wrappers
- Cython now provides only a thin interface with most computations in native C++
- `BaseTrajSeq`, `TrajectoryDataFilter`, `V3dT`, `BCLIBC_Coriolis`, `BCLIBC_Wind`, and `BCLIBC_ShotProps` refactored as C++ classes/enum classes
- Optimized solvers (rk4, euler) and trajectory computations
- Enhanced trajectory data filtering and interpolation
- Unified exception handling in apex, range, and zero-finding calculations

### Fixed
- Memory management across engine and trajectory structures
- Pickling support for `Calculator` interface
- Log level issues
- TDF caching and timestep handling
- Numerical stability including look angles near 90°

### Improved
- Performance through optimized internal data structures using `std::vector`
- Reduced complexity and duplication in Cython wrappers
- Partial compile-time logging disabling to reduce overhead
- Zero-finding and engine computations robustness

## [2.2.5b2] - 2025-11-27
[:simple-github: GitHub release][2.2.5b2]

### Fixed
- `interface::Calculator` custom serialization methods for pickling

## [2.2.5b1] - 2025-11-11
[:simple-github: GitHub release][2.2.5b1]

### Added
- C++ TrajectoryDataFilter implementation

### Changed
- Ported TDF to C++
- Refactored C++ Engine wrapper
- Wrapped `Engine.release_trajectory` in C++

### Fixed
- macOS builds compatibility
- TDF exceptions handling
- `CythonizedBaseIntegrationEngine.integrate` errors check
- Removed useless arguments from integratefunc

## [2.2.4rc1] - 2025-11-09
[:simple-github: GitHub release][2.2.4rc1]

### Added
- Namespace organization improvements
- Helper functions for better code organization

### Changed
- Multiple refactoring passes (Refactor2C_4, Refactor2C_5, Refactor2C_6)
- C-level optimizations for better performance
- Cythonized and C sources updates

### Fixed
- Log level configuration
- Setup process
- Conftest configuration
- TDF cache interpolation for efficiency
- TDF time step check
- Annotations in TDF
- `BCLIBC_Coriolis_adjustRange` function
- Memory management with memset

## [2.2.3] - 2025-10-19
[:simple-github: GitHub release][2.2.3]

### Added
- Python 3.14 and 3.14t support
- ARM wheel building support
- Manual pytest workflow runner for GitHub Actions
- Thread safety improvements for `interface.Calculator`

### Changed
- Dropped support for Python 3.9
- Updated CI workflows to include Python 3.14
- Refactored `WindSock_t` to use built-in structure
- Reduced `.ipynb` dependency footprint for VS Code and PyCharm
- Updated reusable pytest workflows with exit code checks

### Fixed
- Dependency issues for new Python versions
- `Coriolis_t_from_pyobject` handling
- `ShotProps_t_freeResources` to safely NULLIFY internal pointers
- `.pylintrc` issues
- Dependabot configuration

### Removed
- Deprecated runners (macos-13)
- Deprecated workflows (cibuildwheel_test.yml)
- Deprecated `interface.Calculator.cdm` property

## [2.2.2] - 2025-10-16
[:simple-github: GitHub release][2.2.2]

### Added
- Valgrind-based workflows for leak detection
- New benchmarking details in documentation
- `CBaseTrajSeq_t_len` helper function
- Enhanced test helpers and internal data structure creation utilities

### Changed
- Moved integration routines (`_integrate_rk4`, `_integrate_euler`) fully to C
- `CBaseTrajSeq` now wraps pure-C `CBaseTrajSeq_t`
- Replaced Python-level calls with direct C invocations
- Improved `BaseTrajDataT` structure and method access

### Fixed
- Multiple memory leaks in trajectory and curve management
- Enhanced C++ compatibility with `extern "C"` declarations
- Typos and mkdocs build issues
- `termination_reason` checks in C integrators

### Removed
- Redundant pointer dereferences and casts
- Redundant imports and legacy declarations

## [2.2.1] - 2025-10-08
[:simple-github: GitHub release][2.2.1]

### Added
- Import guards for optional dependencies (pandas, numpy, scipy)
- Version-matching guards in `exts`

### Changed
- Updated hooks and contribution guides
- Refreshed code examples for clarity

### Fixed
- Engine loading to prevent import errors when scientific libraries are missing
- Mypy and ruff checks now pass cleanly

### Removed
- Redundant include guard from `bind.c`

## [2.2.0] - 2025-10-03
[:simple-github: GitHub release][2.2.0]

### Added
- New RK4 (Runge-Kutta 4) integrator
- Coriolis effect support in trajectory calculations
- Python 3.13 support
- Entry points for engines
- Override for `getCalcStep` in RK4 engine

### Changed
- Set RK4 engine as default
- Refactored integration with SciPy
- General Cythonization of critical paths
- Some components rewritten directly in C
- Standardized slant terminology
- Restructured and prettified documentation

### Fixed
- RK4 engine implementation
- Type annotations and configuration
- Tests and logger cleanup

### Improved
- Zeroing features and refinements with Cython implementation
- Documentation expanded with user guides and explanations

## [2.2.0rc2] - 2025-09-25
[:simple-github: GitHub release][2.2.0rc2]

### Changed
- Extended documentation

### Fixed
- Various issues from v2.2.0rc1

## [2.2.0rc1] - 2025-09-15
[:simple-github: GitHub release][2.2.0rc1]

### Added
- Entry points for engines
- RK4 integrator with passing tests
- New tests for zeroing
- Coriolis effect implementation

### Changed
- Refactored `trajectory_calc.py`
- Cythonized engines refactoring
- Inline vector operations optimization
- Restructured and prettified documentation
- Updated README

### Fixed
- Test fixes and logger cleanup
- Various SciPy engine configuration issues

## [2.2.0b7] - 2025-08-26
[:simple-github: GitHub release][2.2.0b7]

### Added
- Piecewise Cubic Hermite Interpolation (PCHIP) to trajectory data
- `Optional[RangeError]` to `HitResult`
- Implemented new `dense_output` flag
- Cython-specific unit tests
- Enhanced documentation with standardized docstrings

### Changed
- RK4 engines run with larger `DEFAULT_STEP` for faster results
- Replaced `EngineProtocol.trajectory()` with `.integrate()`
- Rewrote `TrajectoryDataFilter` to interpolate for all requested points
- Rewrote chunks of Cython for better test compatibility
- Renamed `density_factor` to `density_ratio`
- Renamed `PreferredUnits.defaults()` to `.restore_defaults()`

### Deprecated
- `helpers.py::must_fire()` - use `Calculator.fire(raise_range_error=True)` instead
- `extra_data` flag

### Fixed
- Multiple issues including #199, #202, #203, #209, #211, and #35

### Removed
- Dev dependencies from standard install

## [2.2.0b6] - 2025-08-09
[:simple-github: GitHub release][2.2.0b6]

### Added
- ZeroStudy.ipynb with zeroing/fire-solution performance study
- BenchmarkEngines.md analysis
- Enhanced zeroing features

### Changed
- RK4 engine set as default after fixes
- Standardized slant terminology in README
- Cythonized engines refactoring
- Inline vector operations

### Fixed
- RK4 engine implementation
- mkdocs build

### Improved
- All engines now support `.find_max_range()` for any angle

## [2.2.0b5] - 2025-07-04
[:simple-github: GitHub release][2.2.0b5]

### Changed
- Type annotations updates
- Ruff CI setup

### Fixed
- SciPy engine annotations
- SciPy configuration issues

## [2.2.0b4] - 2025-07-01
[:simple-github: GitHub release][2.2.0b4]

### Added
- RK4 `getCalcStep` override

### Changed
- SciPy integration improvements

## [2.2.0b3.post1] - 2025-06-25
[:simple-github: GitHub release][2.2.0b3.post1]

### Changed
- SciPy integration refinements

## [2.2.0b3] - 2025-06-25
[:simple-github: GitHub release][2.2.0b3]

### Changed
- SciPy integration improvements

## [2.2.0b2] - 2025-06-20
[:simple-github: GitHub release][2.2.0b2]

### Changed
- SciPy integration enhancements

## [2.2.0b1] - 2025-06-13
[:simple-github: GitHub release][2.2.0b1]

### Added
- RK4 integrator implementation

### Fixed
- Test suite improvements
- InterfaceConfigDict usages

## [2.1.1b3] - 2025-06-10
[:simple-github: GitHub release][2.1.1b3]

### Added
- Python 3.13 support

## [2.1.1b2] - 2025-06-04
[:simple-github: GitHub release][2.1.1b2]

### Changed
- Refactored `trajectory_calc.py`

## [2.1.1b1] - 2025-06-03
[:simple-github: GitHub release][2.1.1b1]

### Added
- Entry points for engines

## [2.1.0] - 2025-05-22
[:simple-github: GitHub release][2.1.0]

### Added
- Vacuum atmosphere implementation
- Helper utilities and test helpers
- `add_time_of_flight_axis` method
- Enhanced documentation with docstrings
- Automatic CI with UV for better performance

### Changed
- Switched to powder temperature and sensitivity options
- Boostrap Cython modules
- Refactored munition cythonization
- Refactored wind_vector
- Configuration bind refactoring for cythonic TrajectoryCalc

### Fixed
- Atmospheric model issues
- Vector performance (changed to NamedTuple)
- Velocity for temperature calculations
- Exception handling improvements
- Incomplete shot handling
- Trajectories that bend backwards
- `_init_trajectory` issues
- Issue #130

### Improved
- Performance optimizations with high-optimized Euler
- CI pipelines with UV
- Type annotations with Mypy

## [2.1.0rc2] - 2025-04-27
[:simple-github: GitHub release][2.1.0rc2]

### Fixed
- Partial fix to issue #155

## [2.1.0rc1] - 2025-04-13
[:simple-github: GitHub release][2.1.0rc1]

### Fixed
- Completed implementation for issue #164

## [2.1.0b7] - 2025-03-25
[:simple-github: GitHub release][2.1.0b7]

### Added
- Vacuum Atmo implementation
- Unit test for issue #160

### Changed
- Vector changed to NamedTuple for better performance
- Switched CI to UV for performance boost

### Fixed
- All atmospheric model issues from #157
- Simple fix to #160
- CI pipelines
- Mypy typing issues

## [2.1.0b6] - 2025-02-18
[:simple-github: GitHub release][2.1.0b6]

### Changed
- Various improvements and refinements

## [2.1.0b5] - 2025-02-06
[:simple-github: GitHub release][2.1.0b5]

### Added
- Incomplete shot handling

## [2.1.0b4] - 2025-01-25
[:simple-github: GitHub release][2.1.0b4]

### Added
- Helper utilities and test helpers
- `add_time_of_flight_axis` method
- Trusted publishers support

### Changed
- Configuration bind refactoring for cythonic TrajectoryCalc

### Fixed
- Issue #141
- Trajectories that bend backwards

[Unreleased]: https://github.com/o-murphy/py-ballisticcalc/compare/v3.0.0-rc.1...HEAD
[3.0.0-rc.1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v3.0.0-rc.1
[3.0.0-beta.3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v3.0.0-beta.3
[3.0.0-beta.2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v3.0.0-beta.2
[3.0.0-beta.1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.1
[2.3.1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.1
[#339]: https://github.com/o-murphy/py-ballisticcalc/pull/339
[#340]: https://github.com/o-murphy/py-ballisticcalc/pull/340
[2.3.0]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0
[2.3.0rc2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0rc2
[2.3.0rc1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0rc1
[2.3.0b5]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0b5
[2.3.0b4]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0b4
[2.3.0b3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0b3
[2.3.0b2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.3.0b2
[2.2.10]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.10
[2.2.9]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.9
[2.2.8]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.8
[2.2.7]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.7
[2.2.6.post1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.6.post1
[2.2.6]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.6
[2.2.5]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5
[2.2.5rc3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5rc3
[2.2.5rc2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5rc2
[2.2.5rc1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5rc1
[2.2.5b2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5b2
[2.2.5b1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.5b1
[2.2.4rc1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.4rc1
[2.2.3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.3
[2.2.2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.2
[2.2.1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.1
[2.2.0]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0
[2.2.0rc2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0rc2
[2.2.0rc1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0rc1
[2.2.0b7]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b7
[2.2.0b6]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b6
[2.2.0b5]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b5
[2.2.0b4]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b4
[2.2.0b3.post1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b3.post1
[2.2.0b3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b3
[2.2.0b2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b2
[2.2.0b1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.2.0b1
[2.1.1b3]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.1b3
[2.1.1b2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.1b2
[2.1.1b1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.1b1
[2.1.0]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0
[2.1.0rc2]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0rc2
[2.1.0rc1]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0rc1
[2.1.0b7]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0b7
[2.1.0b6]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0b6
[2.1.0b5]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0b5
[2.1.0b4]: https://github.com/o-murphy/py-ballisticcalc/releases/tag/v2.1.0b4
