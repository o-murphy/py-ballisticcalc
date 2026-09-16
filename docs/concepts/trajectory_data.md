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
| `records` | The complete, exact chronological output stream: every scheduled sample and every physical event, each its own row. | `len(result)`, iteration, indexing, `dataframe()`, `plot()` — anything that wants full fidelity. |
| `samples` | Deterministic scheduled RANGE/TIME samples. A sample is annotated with an event's flag only when the two are the same instant to floating-point precision — never merely the nearest one. | Comparing output across engines or solver tolerances, where accepted-step timing differs but the requested schedule does not (its cardinality tracks the schedule, not the integrator's internal steps). |
| `events` | Exact interpolated physical events: ZERO, MACH, APEX, and MRT. | The physical time, position, velocity, or other state at an event. |

`records` backs the everyday container protocol, so `len(result)`,
iteration, indexing, `dataframe()`, and `plot()` all see every exact event
row in its own chronological position — nothing is folded onto a
neighboring sample. Use `samples` instead when you specifically need a
table whose row count doesn't change with solver internals (e.g.
`test_cashkarp_tolerance_controls_adaptive_step_count` relies on this to
compare a tight- and loose-tolerance run row-for-row). A `samples` row
annotated with an event flag is still a scheduled sample; its data must not
be treated as the exact event root — use `events` for that.

`samples` never annotates a sample just because it's the *closest* one —
only when the sample and the event are, in effect, the same instant (an
`HitResult.samples`-level `math.isclose()` check, independent of any
engine's own tolerance settings, which use incompatible units — feet,
state-error rtol, step multiplier — none of them a time tolerance). With a
coarse schedule this matters: `trajectory_range == trajectory_step` leaves
only the launch and terminal samples, so an APEX or ZERO in between is not
genuinely close to either one — it stays unannotated in `samples` (visible
only in `events`) rather than getting glued onto whichever endpoint
bisection happens to prefer, which would otherwise misrepresent that
endpoint's own state as the event's.

```python
result = calc.fire(shot, trajectory_range=Distance.Yard(1_000), flags=TrajFlag.ALL)

# Full-fidelity output: every event gets its own exact row.
for row in result:  # equivalent to `for row in result.records`
    print(row.distance, row.flag)

# Exact event state.
zero_down = result.flag(TrajFlag.ZERO_DOWN)
mach_transition = result.flag(TrajFlag.MACH)
all_events = result.events

# Deterministic schedule table, e.g. to compare two engines row-for-row.
schedule = result.samples
```

!!! warning "`HitResult.trajectory` is deprecated"
    Before this release's `records`/`samples`/`events` split, `trajectory`
    was the only view, and it had `samples`' semantics (event flags folded
    onto the nearest scheduled row). `HitResult.trajectory` is now a
    deprecated alias for `records` — kept so old code still runs, but with
    `records`' row count/order, not the old `trajectory`'s. Code that
    indexed `.trajectory` assuming a fixed RANGE/TIME-schedule cardinality
    should switch to `.samples`; code that just wanted every point should
    switch to `.records` (or drop the attribute and iterate the
    `HitResult` directly).

The compatibility constructor spelling `HitResult(..., trajectory=rows)` is
still accepted; its rows are interpreted as `records` before these views are
derived.
