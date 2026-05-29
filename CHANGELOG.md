# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `py_ballisticcalc.exts` (`bind.pyx`): `BCLIBC_ShotProps_from_pyobject` is now a thin field mapper — fills `BCLIBC_Shot` with natural-unit values and delegates all physics/unit conversions to `BCLIBC_Shot::to_shot_props()` in C++ (cant cos/sin, CIPM-2007 atmosphere, Coriolis trig, PCHIP drag curve, wind sock assembly); Step 2 of bclibc-wrapper-consolidation
- `py_ballisticcalc.exts` (`base_types.pxd`): added `BCLIBC_Shot` cppclass declaration
- `py_ballisticcalc.exts` (`base_types.pxd`): `BCLIBC_Coriolis` cppclass extended with `@staticmethod from_lat_az(lat_deg, muzzle_velocity_fps, az_deg)`
- `py_ballisticcalc.exts` (`base_types.pxd`): `BCLIBC_Atmosphere` cppclass extended with `@staticmethod from_conditions(t_c, p_hpa, alt_ft, humidity)`
- `py_ballisticcalc.exts` (`bind.pyx`): added `BCLIBC_Coriolis_from_lat_az` and `BCLIBC_Atmosphere_from_conditions` Cython helpers (available for callers that hold Python domain objects directly; `_from_pyobject` variants retained for the same reason)
- bclibc submodule bumped to [`v1.1.2`](https://github.com/ballistics-lab/bclibc) — adds `BCLIBC_Shot` / `to_shot_props()`, `BCLIBC_Coriolis::from_lat_az()`, `BCLIBC_Atmosphere::from_conditions()` (Steps 1–2); renames all `BC*` struct/enum types in `bclibc_ffi.h` to `BCLIBCFFI_*` and adds `BCLIBCFFI_*_shot()` entry points in the C FFI layer (Step 3a, breaking for C FFI consumers); no effect on Cython path (`base_types.hpp` `BCLIBC_*` types are unchanged)
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

### Fixed
- `CythonizedBaseTrajData.__str__` unpacked `(name, value)` from an iterator that yields scalar values — raised `ValueError` on any call
- `Vacuum.__init__` (`conditions.py`): `Atmo.__init__` uses `pressure or standard_pressure(...)` so passing `pressure=0` (falsy) stores `_p0 = 1013.25 hPa` instead of `0`; `Vacuum.__init__` corrected `_pressure` and `_density_ratio` but not `_p0`; any C++ wrapper reading `_p0` directly (e.g. Dart FFI, WASM) would receive 1013.25 hPa for vacuum; fix: explicitly set `self._p0 = 0.0` in `Vacuum.__init__` after `super().__init__()`
- `BCLIBC_ShotProps_from_pyobject` (`bind.pyx`): `shot_info.winds` was accessed twice (once for `len()`, once for the for-loop); `Shot.winds` returns `tuple(self._winds)` — a new tuple on every call; under free-threading a concurrent mutation of `_winds` between the two accesses could make `wind_count > winds_vec.size()`, causing an out-of-bounds read in `BCLIBC_Shot::to_shot_props()`; fix: cache `winds_py = shot_info.winds` once before both uses
- `BCLIBC_ShotProps_from_pyobject` (`bind.pyx`): `shot_info.ammo`, `.ammo.dm`, `.atmo`, and `.weapon` were traversed multiple times each without being cached in `cdef object` locals, violating the function's own documented invariant ("Cython may forget to add DECREF") — each chain traversal creates a temporary reference that Cython may not release on exception paths; fix: cache all intermediates in named `cdef object` locals at the top of the function

### CI
- `test_full_matrix` in `pytest-cythonized-rk4-engine.yml` and `pytest-cythonized-euler-engine.yml`: changed `fail-fast` from `false` to `true` — stops the 24-job matrix on the first failure instead of running all jobs to completion

### Removed
- Python 3.10 support EOL - removed all references to Python 3.10, updated CI and dependencies

### CI
- `py_ballisticcalc.exts` wheels now target the Python stable ABI (`cp311-abi3-*`): one binary per platform/architecture is compatible with CPython 3.11 and all later standard releases; free-threaded Python 3.13t / 3.14t is built as separate version-specific wheels
- `cibuildwheel` build selectors: `cp311-* cp313t-* cp314t-*`; `cp313t-*` requires `enable = ["cpython-freethreading"]` in cibuildwheel 3.4 (flag is deprecated but `cp313t` is silently skipped without it)
- Cythonized engine test full matrix: `3.11, 3.14` (abi3 boundary versions) + `3.13t, 3.14t` (distinct free-threaded ABIs); `3.12`, `3.13` removed — abi3 binary is identical across standard CPython versions
- `pypi-publish.yml`: extracted `build-sdist` job — pure Python wheel and exts sdist built once on `ubuntu-latest`; removed from per-OS `build` matrix jobs to eliminate 5× redundant platform-independent builds
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

[Unreleased]: https://github.com/o-murphy/py-ballisticcalc/compare/v2.2.10...HEAD
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
