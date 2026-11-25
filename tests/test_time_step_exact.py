"""Time rows of ``integrate(..., time_step=...)`` sit on the requested grid for every engine (C11).

The cythonized wrapper used to declare ``float time_step`` (32-bit), so ``0.3`` became ``0.30000001192...`` and the
k-th time row was late by about ``k * 1.2e-8`` s compared with the pure-Python engines.

C24 (SciPy) extends it to the tail after the last range row and to ``dist_step=0``.

Run per engine, e.g. ``pytest tests/test_time_step_exact.py --engine=cythonized_rk4``.
"""

import pytest

from py_ballisticcalc import Ammo, DragModel, Shot, TableG7, TrajFlag, Weapon
from py_ballisticcalc.unit import Distance, Velocity, Weight
from tests.repin_xfail import xfail_until_repin

pytestmark = pytest.mark.engine

TOL = 1e-12  # s; a 32-bit time_step misses it by 1.2e-8 s at the first row after t = 0
# s; tiny_bclibc single precision (float32): row times are float32-rounded and its schedule accumulates time in float32
# (error grows with trajectory length: 5.3e-6 s observed on the cases below, ~1.7e-4 s on 6000 m / dt 0.01).
# A deliberate difference of that engine (tiny_bclibc/README.md, "Deliberate differences"); double keeps TOL.
TINY_SINGLE_TOL = 5e-5


def _tol(engine) -> float:
    """Time tolerance for the engine: float32 tiny_bclibc is looser, every other engine (also tiny double) is exact."""
    module = getattr(engine, "__module__", "") or ""
    if module.startswith("tiny_bclibc") and "Single" in engine.__name__:
        return TINY_SINGLE_TOL
    return TOL


def _shot() -> Shot:
    dm = DragModel(0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(weapon=Weapon(sight_height=Distance.Meter(0.05)), ammo=Ammo(dm, Velocity.MPS(800)))


@pytest.mark.parametrize("time_step", [0.3, 0.1, 0.35])
def test_time_rows_are_on_the_time_grid(loaded_engine_instance, time_step):
    """Row k of the time schedule has ``time == k * time_step`` (the last row is the range end, not a time row)."""
    tol = _tol(loaded_engine_instance)
    engine = loaded_engine_instance({})
    res = engine.integrate(
        _shot(),
        Distance.Meter(3000),
        dist_step=Distance.Meter(100000),  # no RANGE row but start and end: the rest are time rows
        time_step=time_step,
        filter_flags=TrajFlag.RANGE,
    )
    rows = res.records[:-1]
    assert len(rows) >= 5, f"expected several time rows, got {len(rows)}"
    for k, row in enumerate(rows):
        assert row.time == pytest.approx(k * time_step, abs=tol, rel=0), (
            f"row {k}: time {row.time!r} != {k * time_step!r} (error {row.time - k * time_step:.3e} s)"
        )


# region C24: the time schedule runs over the whole trajectory, also past the last range row

RK4_TOL = 5e-3  # s; engines integrate differently, the time grid itself is exact but a row is a time on that grid


def _rows(engine_cls, dist_m: float, step_m: float, time_step: float):
    return (
        engine_cls({})
        .integrate(
            _shot(),
            Distance.Meter(dist_m),
            dist_step=Distance.Meter(step_m),
            time_step=time_step,
            filter_flags=TrajFlag.RANGE,
        )
        .records
    )


def _rk4():
    from py_ballisticcalc.engines import RK4IntegrationEngine

    return RK4IntegrationEngine


def test_large_dist_step_keeps_time_rows(loaded_engine_instance):
    """Range 1500 m, dist_step 5000 m: only the start range row, then the time rows 0, 0.3 ... to the end."""
    rows = _rows(loaded_engine_instance, 1500, 5000, 0.3)
    ref = _rows(_rk4(), 1500, 5000, 0.3)
    tol = _tol(loaded_engine_instance)
    times = [r.time for r in rows]
    assert len(times) == len(ref) >= 12, f"expected time rows 0..3.3 s, got {times}"
    for k, (t, rt) in enumerate(zip(times, [r.time for r in ref])):
        assert t == pytest.approx(k * 0.3, abs=tol, rel=0)
        assert t == pytest.approx(rt, abs=tol, rel=0)


def test_zero_dist_step_with_time_step(loaded_engine_instance):
    """dist_step=0 means no range rows (not a ZeroDivisionError): only the time schedule, as for rk4."""
    rows = _rows(loaded_engine_instance, 1500, 0, 0.3)
    ref = _rows(_rk4(), 1500, 0, 0.3)
    assert len(rows) == len(ref) >= 12
    tol = _tol(loaded_engine_instance)
    for k, row in enumerate(rows):
        assert row.time == pytest.approx(k * 0.3, abs=tol, rel=0)


@pytest.mark.parametrize("step_m", [500, 1500, 5000])
@pytest.mark.parametrize("time_step", [0.0, 0.3])
def test_row_count_matches_rk4(loaded_engine_instance, request, step_m, time_step):
    if time_step == 0.3 and step_m in (500, 1500):
        xfail_until_repin(request, loaded_engine_instance)
    rows = _rows(loaded_engine_instance, 1500, step_m, time_step)
    ref = _rows(_rk4(), 1500, step_m, time_step)
    assert len(rows) == len(ref), f"{len(rows)} rows != rk4's {len(ref)}"
    for row, r in zip(rows, ref):
        assert row.time == pytest.approx(r.time, abs=RK4_TOL, rel=0)


# endregion C24
