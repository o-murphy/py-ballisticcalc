"""The time rows due before a RANGE row are kept, also when one wide step holds both (matches bclibc ``emit_time_rows``).

A RANGE row restarts the time schedule from its own time; the filter used to emit the range rows of a step before its
time rows, so a wide step holding the last time row (t = 3.3 s of a 0.3 s ``time_step``) and the row at the range limit
lost the time row. RK4, Euler and Verlet have small steps and rarely show it, so the synthetic ``record_step`` test feeds
the filter a wide step directly.

Run per engine, e.g. ``pytest tests/test_time_rows_before_range_end.py --engine=scipy_dp``.
"""

import itertools

import pytest

from py_ballisticcalc import Ammo, DragModel, Shot, TableG7, TrajFlag, Weapon
from py_ballisticcalc.conditions import Atmo
from py_ballisticcalc.engines.base_engine import TrajectoryDataFilter
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.trajectory_data import BaseTrajData
from py_ballisticcalc.unit import Angular, Distance, Velocity, Weight
from py_ballisticcalc.vector import Vector

pytestmark = pytest.mark.engine

TIME_STEP = 0.3
RANGE_M = 1500
FT_PER_M = 1 / 0.3048
POS_TOL_M = 0.5  # m; the integrators differ ~0.03 m (Euler ~0.2 m)
TIME_TOL = 1e-3  # s


def _shot() -> Shot:
    dm = DragModel(0.243, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.05)),
        ammo=Ammo(dm, Velocity.MPS(800)),
        relative_angle=Angular.Degree(0.15),
    )


def _rows(engine_cls, dist_step_m: float):
    return (
        engine_cls({})
        .integrate(
            _shot(),
            Distance.Meter(RANGE_M),
            dist_step=Distance.Meter(dist_step_m),
            time_step=TIME_STEP,
            filter_flags=TrajFlag.RANGE,
        )
        .records
    )


def _rk4():
    from py_ballisticcalc.engines import RK4IntegrationEngine

    return RK4IntegrationEngine


@pytest.mark.parametrize("dist_step_m", [500, 1500])
def test_time_row_before_range_end_is_kept(loaded_engine_instance, dist_step_m):
    rows = _rows(loaded_engine_instance, dist_step_m)
    ref = _rows(_rk4(), dist_step_m)
    times = [r.time for r in rows]
    assert len(rows) == len(ref), f"{len(rows)} rows != rk4's {len(ref)}: {times} vs {[r.time for r in ref]}"

    # every row after the first is a time row (previous row + time_step) or a range row (multiple of dist_step / the end)
    time_rows = 0
    for prev, row in itertools.pairwise(rows):
        x_m = row.distance >> Distance.Meter
        is_range = abs(x_m / dist_step_m - round(x_m / dist_step_m)) * dist_step_m < 1e-3 or abs(x_m - RANGE_M) < 1e-3
        is_time = abs(row.time - prev.time - TIME_STEP) < 1e-9
        assert is_range or is_time, f"row t={row.time} x={x_m} m is neither a time row nor a range row: {times}"
        time_rows += is_time
    assert time_rows >= 10

    # the last time row before the end row is present: the row before the end row is a time row
    assert len(rows) >= 3
    assert rows[-2].time - rows[-3].time == pytest.approx(TIME_STEP, abs=1e-9, rel=0), f"last time row lost: {times}"
    assert rows[-2].time < rows[-1].time
    assert (rows[-1].distance >> Distance.Meter) == pytest.approx(RANGE_M, abs=1e-3)

    for row, r in zip(rows, ref):
        assert row.time == pytest.approx(r.time, abs=TIME_TOL, rel=0)
        assert (row.distance >> Distance.Meter) == pytest.approx(r.distance >> Distance.Meter, abs=POS_TOL_M, rel=0)


def _props() -> ShotProps:
    dm = DragModel(bc=0.243, drag_table=TableG7)
    return ShotProps.from_shot(Shot(ammo=Ammo(dm, mv=Velocity.FPS(2600)), weapon=Weapon(), atmo=Atmo.icao()))


def test_filter_wide_step_emits_time_rows_before_range_row():
    """One wide step 0 -> 1.0 s at 100 ft/s with a range row at 65 ft (t = 0.65) and a time step 0.3.

    Time rows 0.3 and 0.6 are strictly before the range row and come first; the range row restarts the clock, so the
    next time row is 0.95 (65 ft + 0.3 s).
    """
    flt = TrajectoryDataFilter(_props(), TrajFlag.NONE, range_limit=200.0, range_step=65.0, time_step=0.3)
    start = BaseTrajData(0.0, Vector(0.0, 0.0, 0.0), Vector(100.0, 0.0, 0.0), 1100.0)
    end = BaseTrajData(1.0, Vector(100.0, 0.0, 0.0), Vector(100.0, 0.0, 0.0), 1100.0)
    flt.record_initial(start)
    flt.record_step(start, end)
    times = [r.time for r in flt.records]
    assert times == pytest.approx([0.0, 0.3, 0.6, 0.65, 0.95], abs=1e-9, rel=0)
    assert [bool(r.flag & TrajFlag.RANGE) for r in flt.records] == [True] * 5
