# Engines

## Summary

py-ballisticcalc provides various calculation engines with identical public semantics.  The relative merits of the engines are detailed in [benchmarks](benchmarks.md).

| Engine Name                                                                                            | Speed (Find Zero / Trajectory)                |        Dependencies         | Description                                       |
| :----------------------------------------------------------------------------------------------------- | :-------------------------------------------- | :-------------------------: | :------------------------------------------------ |
| **[`rk4_engine`][py_ballisticcalc.engines.RK4IntegrationEngine]**                                      | Baseline (1x)                                 |        None; default        | Runge-Kutta 4th-order integration                 |
| [`euler_engine`][py_ballisticcalc.engines.EulerIntegrationEngine]                                      | :material-arrow-down:    0.5x / 0.5x (slower) |            None             | Euler 1st-order integration                       |
| [`verlet_engine`][py_ballisticcalc.engines.VelocityVerletIntegrationEngine]                            | :material-arrow-down:   0.8x / 0.8x (slower)  |            None             | Verlet 2nd-order symplectic integration           |
| [`cythonized_rk4_engine`][py_ballisticcalc_exts.CythonizedRK4IntegrationEngine]                        | :material-arrow-up:   205x / 144x (faster)    | [`[exts]`](#cython-engines) | Compiled Runge-Kutta 4th-order                    |
| [`cythonized_euler_engine`][py_ballisticcalc_exts.CythonizedEulerIntegrationEngine]                    | :material-arrow-up:    54x / 52x (faster)     | [`[exts]`](#cython-engines) | Compiled Euler integration                        |
| [`cythonized_verlet_engine`][py_ballisticcalc_exts.CythonizedVelocityVerletIntegrationEngine]          | :material-arrow-up:   130x / 99x (faster)     | [`[exts]`](#cython-engines) | Compiled Verlet 2nd-order symplectic              |
| [`cythonized_rkck_engine`][py_ballisticcalc_exts.CythonizedCashKarpIntegrationEngine][^adaptive]       | :material-arrow-up: ~3370x / ~335x (faster)   | [`[exts]`](#cython-engines) | Compiled Cash-Karp adaptive RK45                  |
| [`cythonized_dopri_engine`][py_ballisticcalc_exts.CythonizedDormandPrinceIntegrationEngine][^adaptive] | :material-arrow-up: ~3370x / ~335x (faster)   | [`[exts]`](#cython-engines) | Dormand--Prince 5(4), SciPy RK45-style controller |
| [`scipy_engine`][py_ballisticcalc.engines.SciPyIntegrationEngine]                                      | :material-arrow-up:  4.6x / 8.3x (faster)     |          `[scipy]`          | Advanced numerical methods                        |

The current rows for `rk4_engine`, Cython RK4/Euler/Cash-Karp, and SciPy were measured with
`scripts/benchmark.py -w 100 -r 1000` on one machine and one revision.  The two figures in each
cell are **Find Zero / Trajectory**, calculated directly from that run's pure-Python
`rk4_engine` means (242.586 ms / 55.271 ms).  Treat them as hardware- and workload-dependent
measurements, not portable constants.  The remaining historical rows should be remeasured
before comparing them numerically with this snapshot.  Raw Cash-Karp figures are in
[benchmarks](benchmarks.md#cash-karp-engine).

[^adaptive]: Measured directly against pure-Python `rk4_engine`, not composed through
`cythonized_rk4_engine`'s own row above. See [Adaptive integration
(Cash-Karp)](#adaptive-integration-cash-karp) below for why Find Zero and Trajectory differ so
much for `cythonized_rkck_engine` even when comparing just the two Cython engines directly.

* This project will default to the [`rk4_engine`][py_ballisticcalc.engines.RK4IntegrationEngine].
* For higher speed and precision use the [`scipy_engine`][py_ballisticcalc.engines.SciPyIntegrationEngine].
* For maximum speed use the [`cythonized_rk4_engine`][py_ballisticcalc_exts.CythonizedRK4IntegrationEngine] (or [`cythonized_rkck_engine`][py_ballisticcalc_exts.CythonizedCashKarpIntegrationEngine] for repeated/zero-finding-heavy workloads — see below).

To select a specific engine when creating a [`Calculator`][py_ballisticcalc.interface.Calculator], use the optional `engine` argument:

```python
from py_ballisticcalc import Calculator
calc = Calculator(engine="rk4_engine")
# or via entry-point path
calc = Calculator(engine="my_pkg.my_mod:MyEngine")
```

## Cython Engines

Cythonized engines are compiled for maximum performance.  Include the `[exts]` option to install those:

=== "pip"
    ```bash
    pip install "py-ballisticcalc[exts]"
    ```
    
=== "uv"
    ```bash
    uv add py-ballisticcalc[exts]
    ```

## Adaptive integration (Cash-Karp, Dormand-Prince)

`cythonized_dopri_engine` is a companion Dormand--Prince 5(4) engine. It uses
scalar `relative_tolerance` and `absolute_tolerance` (both default to `1e-6`),
SciPy RK45 component scaling, safety `0.9`, and factors in `[0.2, 10]`.
Cash-Karp intentionally keeps its existing controller for compatibility.

`cythonized_rkck_engine` (`py_ballisticcalc_exts.CythonizedCashKarpIntegrationEngine`) wraps
[bclibc](https://github.com/ballistics-lab/bclibc)'s Cash-Karp adaptive RK45 integrator
(Numerical Recipes' `rkck`, an embedded 4th/5th-order method). Unlike every other engine here,
its internal step size is adaptive rather than fixed *only* by `cStepMultiplier`:
`cStepMultiplier` sets the configured base step, and Cash-Karp grows it up to 64x during smooth
flight or shrinks it down to 1/64 whenever its embedded error estimate
exceeds its SciPy-compatible tolerances, `relative_tolerance` and scalar
`absolute_tolerance` (both default `1e-6`, configurable per instance). Each of the three
position and three velocity state components is scaled independently as
`atol + rtol * max(abs(y), abs(y_new))`; their scaled errors are combined with an RMS norm,
matching `scipy.integrate.solve_ivp`'s Runge-Kutta controllers. This needs far fewer
accepted steps than fixed-step RK4 for comparable accuracy.

That step-count reduction alone doesn't explain why `set_weapon_zero`'s speedup (~16x vs.
`cythonized_rk4_engine`) is so much larger than a single `fire()` call's (~2.3x): both compare the
same pair of engines on the same 2000m shot. The difference is where the Python/C++ call
boundary falls. `fire()` crosses that boundary once per call, but still pays a roughly fixed
per-call cost (unit conversions, building `HitResult`/`TrajectoryData` rows) on top of the raw
integration — a cost that's a small fraction of `cythonized_rk4_engine`'s comparatively slow raw
integration, but a much larger fraction of `cythonized_rkck_engine`'s (already tiny) raw
integration, so it dilutes CK's apparent advantage. `set_weapon_zero`, by contrast, crosses that
boundary once for the *entire* damped-Newton search (confirmed by measurement: 4 iterations for
this shot, each internally calling the integrator with no per-iteration Python round-trip), so
the fixed per-call cost is paid once instead of once per iteration, and the ratio that comes
through is much closer to the engines' raw, undiluted integration speeds. Neither number is
wrong; they answer different questions ("how much faster is a typical Python-facing call" vs.
"how much faster is the raw integration"). See the [benchmarks](benchmarks.md) page for the
measurements.

```python
from py_ballisticcalc import Calculator
calc = Calculator(engine="cythonized_rkck_engine")
# or, to tune the error tolerance:
from py_ballisticcalc_exts import CythonizedCashKarpIntegrationEngine
calc = Calculator(engine=CythonizedCashKarpIntegrationEngine(
    {"relative_tolerance": 1e-6, "absolute_tolerance": 1e-6}
))
```

Two things had to be fixed to make this correct, not just fast — both apply to every engine now,
not only Cash-Karp:

1. **Per-stage recompute, not per-step memoization.** Fixed-step RK4 evaluates the drag
   coefficient once per step and reuses it across all 4 sub-stages — a fine approximation
   because the step is always tiny. An adaptive method cannot do this: Cash-Karp recomputes the
   drag coefficient *and* the atmosphere sample fresh at each of its 6 stages. An earlier
   attempt that reused RK4's freeze-once trick produced real, tolerance-independent accuracy
   failures, because the embedded error estimator is blind to model error from a stale
   drag/atmosphere sample — it only measures discretization error of the frozen sub-problem, so
   tightening `relative_tolerance` never helped.
2. **Event/row interpolation had to stop assuming dense, uniform raw samples.** The original
   per-point interpolation scheme estimated a Hermite slope from the spacing of 3 neighboring
   raw integration points (finite-difference PCHIP) — accurate when those points are close
   together and evenly spaced (true of RK4's fixed tiny step), but measurably wrong once an
   adaptive integrator legitimately takes few, large steps through smooth flight: a multi-unit
   miss on a ZERO/MACH/APEX crossing was observed and reproduced. The fix streams each accepted
   `(start, end)` interval to the trajectory filter and reconstructs RANGE/TIME rows and event
   roots with a 2-point cubic Hermite built from that interval's *exact* endpoint position and
   velocity (no finite-difference estimate), solved by bisection where a crossing is sought.
   Velocity at an interpolated point is the derivative of that same position Hermite, not a
   separately-interpolated series, so position and velocity stay mutually consistent. A
   consequence: a scheduled sample and a physical event are no longer merged into one row just
   because their timestamps happen to land close together — see
   [`HitResult` output views](trajectory_data.md#hitresult-output-views). This fix applies to
   every engine's `handle_step`/`record_step` path, not only Cash-Karp's, so `rk4_engine` and
   `cythonized_rk4_engine` benefit from the same accuracy improvement even though their fixed,
   dense step rarely exposed the original bug.

## Custom Engines

**To define a custom engine:** Create a separate module with a class that implements the [`EngineProtocol`][py_ballisticcalc.generics.engine.EngineProtocol].
The engine's constructor should implement [`EngineFactoryProtocol`][py_ballisticcalc.generics.engine.EngineFactoryProtocol]
You can then load it like:
```python
from py_ballisticcalc import Calculator

calc = Calculator(engine="my_library.my_module:MyAwesomeEngine")
```

**Entry Point:** You can also give the engine a named entry point in `pyproject.toml`/`setup.py`.  The entry point name should end with `_engine`.  Example:

```toml
[project.entry-points.py_ballisticcalc]
my_awesome_engine = "my_library.my_module:MyAwesomeEngine"
```

Then you can load the engine using the entry point name:
```python
from py_ballisticcalc import Calculator

calc = Calculator(engine="my_awesome_engine")
```

**Test a custom engine**

To test a specific engine with the project test suite, run `pytest` with `--engine` argument.  Examples:
```shell
pytest ./tests --engine="my_awesome_engine" 
# or
pytest ./tests --engine="my_library.my_module:MyAwesomeEngine" 
```
