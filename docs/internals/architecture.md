# Architecture Overview

**Goals**

- Keep a compact, well-tested ballistic calculator.
- Provide multiple integration engines (pure-Python and Cython-accelerated engines).
- Expose consistent APIs and event semantics (zero crossings, Mach crossing, apex) across engines.

## High-level layers

### 1. Public API
- [`Calculator`][py_ballisticcalc.interface.Calculator] is the top-level interface used by most clients.

### 2. Scene / shot description
- [py_ballisticcalc.shot.Shot][] captures the shot parameters: `ammo`, `weapon`, `look_angle`, `relative_angle`, `wind` and atmosphere.
- [Ammo][py_ballisticcalc.munition.Ammo], [Weapon][py_ballisticcalc.munition.Weapon], and [Atmo][py_ballisticcalc.conditions.Atmo] live in `py_ballisticcalc.munition.py` and `py_ballisticcalc.conditions.py`.

### 3. Drag model
- [py_ballisticcalc.drag_model][] and [py_ballisticcalc.drag_tables][] provide the drag lookup and interpolation used by the integrators.

### 4. Integration engines
- Engines implement [EngineProtocol][py_ballisticcalc.interface.EngineProtocol] (see `py_ballisticcalc.generics.engine`).
- Cython engines are compiled in `py_ballisticcalc.exts/py_ballisticcalc_exts` for performance.  See `rk4_engine.pyx` and `euler_engine.pyx` implementations.
  
### 5. Trajectory data and events
- `py_ballisticcalc.trajectory_data.py` defines [`TrajFlag`][py_ballisticcalc.trajectory_data.TrajFlag], [`BaseTrajData`][py_ballisticcalc.trajectory_data.BaseTrajData], [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData], and [`HitResult`][py_ballisticcalc.trajectory_data.HitResult].
- [`TrajFlag`][py_ballisticcalc.trajectory_data.TrajFlag] event flags include: `ZERO_UP`, `ZERO_DOWN`, `MACH`, `RANGE`, `APEX`, and they are recorded with union semantics when they occur within a small time window.
- [py_ballisticcalc.engines.base_engine.TrajectoryDataFilter][]:
    - Converts raw step samples to recorded `TrajectoryData` rows.
    - Handles sampling by range/time.
    - Detects `TrajFlag` events and performs interpolation for precise event timestamps/values.
    - Applies unioning of flags within `BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA`.

### 6. Search helpers
- The engine provides root-finding and search helpers implemented on top of the `integrate()` method:
    - `zero_angle`, which falls back on the more computationally demanding but reliable `find_zero_angle`, finds `barrel_elevation` to hit a sight distance.
    - `find_max_range` finds angle that maximizes slant range.
    - `find_apex` finds the apex, which is where vertical velocity crosses from positive to negative.
- To ensure parity between engines, these searches run the same Python-side logic and temporarily relax termination constraints where needed.

## Integration details & parity
- Cython engines return dense [BaseTrajData][py_ballisticcalc.trajectory_data.BaseTrajData] samples; Python [py_ballisticcalc.engines.base_engine.TrajectoryDataFilter][] is responsible for event interpolation. This design keeps the high-level semantics in one place and reduces duplication.
