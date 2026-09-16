# Trajectory Data

Data structures and helpers for computed trajectories:

- [`TrajFlag`][py_ballisticcalc.trajectory_data.TrajFlag]: Flags marking events (`ZERO_UP`, `ZERO_DOWN`, `MACH`, `RANGE`, `APEX`, etc.).
- [`BaseTrajData`][py_ballisticcalc.trajectory_data.BaseTrajData]: Minimal record of integration steps that can be used to interpolate for any [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData] point.
- [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]: Rich unit-aware rows for presentation/analysis.
- [`HitResult`][py_ballisticcalc.trajectory_data.HitResult]: Container with convenience lookups and plotting/dataframe helpers.
- [`DangerSpace`][py_ballisticcalc.trajectory_data.DangerSpace]: Analyze tolerance to ranging error at a given distance and target height.

## `HitResult` output views

`HitResult` exposes the same calculation through three views. Choose the
view by the question being asked, rather than relying on an implicit
time-tolerance merge between a scheduled row and a physical event.

| View | Contents | Use it for |
| --- | --- | --- |
| `trajectory` | Deterministic scheduled RANGE/TIME samples. Nearby event flags are annotated on the closest sample. | Tables, plots, indexing, and a stable row count. |
| `events` | Exact interpolated physical events: ZERO, MACH, APEX, and MRT. | The physical time, position, velocity, or other state at an event. |
| `records` | The complete chronological output stream before table projection. | Integrator-level consumers that need both scheduled samples and exact event rows. |

`trajectory` is the normal public table, so `len(result)`, iteration,
indexing, `dataframe()`, and plotting all use it. Its cardinality follows
the requested RANGE/TIME schedule rather than accepted integration steps or
whether an event happens to land close to a scheduled sample. An annotated
row is a scheduled sample; its data must not be treated as the exact event
root.

```python
result = calc.fire(shot, trajectory_range=Distance.Yard(1_000), flags=TrajFlag.ALL)

# Stable output table for presentation.
for sample in result.trajectory:
    print(sample.distance, sample.flag)

# Exact event state.
zero_down = result.flag(TrajFlag.ZERO_DOWN)
mach_transition = result.flag(TrajFlag.MACH)
all_events = result.events

# Unprojected chronological stream, when the distinction matters.
raw_records = result.records
```

The compatibility constructor spelling `HitResult(..., trajectory=rows)` is
still accepted; its rows are interpreted as `records` before these views are
derived.
