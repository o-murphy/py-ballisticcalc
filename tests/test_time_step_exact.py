"""Time rows of ``integrate(..., time_step=...)`` sit on the requested grid for every engine (C11).

The cythonized wrapper used to declare ``float time_step`` (32-bit), so ``0.3`` became ``0.30000001192...`` and the
k-th time row was late by about ``k * 1.2e-8`` s compared with the pure-Python engines.

Run per engine, e.g. ``pytest tests/test_time_step_exact.py --engine=cythonized_rk4``.
"""

import pytest

from py_ballisticcalc import Ammo, DragModel, Shot, TableG7, TrajFlag, Weapon
from py_ballisticcalc.unit import Distance, Velocity, Weight

pytestmark = pytest.mark.engine

TOL = 1e-12  # s; a 32-bit time_step misses it by 1.2e-8 s at the first row after t = 0


def _shot() -> Shot:
    dm = DragModel(0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(weapon=Weapon(sight_height=Distance.Meter(0.05)), ammo=Ammo(dm, Velocity.MPS(800)))


@pytest.mark.parametrize("time_step", [0.3, 0.1, 0.35])
def test_time_rows_are_on_the_time_grid(loaded_engine_instance, time_step):
    """Row k of the time schedule has ``time == k * time_step`` (the last row is the range end, not a time row)."""
    if "SciPy" in loaded_engine_instance.__name__:
        pytest.skip("SciPy engine does not produce a time-step schedule (only the start row) in this call; not C11")
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
        assert row.time == pytest.approx(k * time_step, abs=TOL, rel=0), (
            f"row {k}: time {row.time!r} != {k * time_step!r} (error {row.time - k * time_step:.3e} s)"
        )
