# Trajectory Data

Data structures and helpers for computed trajectories:

- [`TrajFlag`][py_ballisticcalc.trajectory_data.TrajFlag]: Flags marking events (`ZERO_UP`, `ZERO_DOWN`, `MACH`, `RANGE`, `APEX`, etc.).
- [`BaseTrajData`][py_ballisticcalc.trajectory_data.BaseTrajData]: Minimal record of integration steps that can be used to interpolate for any [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData] point.
- [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]: Rich unit-aware rows for presentation/analysis.
- [`HitResult`][py_ballisticcalc.trajectory_data.HitResult]: Container with convenience lookups and plotting/dataframe helpers.
- [`DangerSpace`][py_ballisticcalc.trajectory_data.DangerSpace]: Analyze tolerance to ranging error at a given distance and target height.
