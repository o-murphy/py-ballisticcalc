# Trajectory Data

??? api "API Documentation"

    [`py_ballisticcalc.trajectory_data`][py_ballisticcalc.trajectory_data]<br>

Data structures and helpers for computed trajectories:

- `TrajFlag`: Flags marking events (ZERO_UP/DOWN, MACH, RANGE, APEX, etc.).
- `BaseTrajData`: Minimal internal state for dense stepping (feet/seconds).
- `TrajectoryData`: Rich unit-aware rows for presentation/analysis.
- `HitResult`: Container with convenience lookups and plotting/dataframe helpers.
- `DangerSpace`: Analyze tolerance to ranging error at a given distance and target height.
