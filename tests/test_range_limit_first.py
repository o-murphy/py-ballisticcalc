"""The range limit is decided before the altitude / drop / velocity limits (the order of the C++ core).

A step that crosses the range limit AND a limit in the same step ends the shot at the range limit: no ``RangeError`` and
no extra row after the row at the range limit.  Before, the Python integrators tested the limits after the step that
crossed the range limit, so a shot toward a target on a nearly vertical line of sight (look -89.9 degrees: the range limit
in x is ~2.9 ft while the shot falls 1600 ft in the same step) raised ``RangeError`` and left a point past the target as the
last row.  The zero search then failed to converge ("Distance non-convergent") and fell back to a Ridder search that did
not return in minutes.
"""

import math
import signal

import pytest

from py_ballisticcalc import BaseEngineConfigDict, Calculator, RangeError
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

LOOK_DEG = -89.9
TARGET_M = 500.0
# Barrel elevation of the steep shot the rows were recorded for (a zero of this shot, radians).
BARREL_RAD = -1.569042498149
# Minimum altitudes (ft) for which the step that crosses the range limit also crosses the altitude limit:
# the step end of each integrator lies at a different depth, so each integrator is hit by one of them.
MIN_ALTITUDES_FT = (-1641.0, -1640.5, -1640.44)


class _Hang(Exception):
    pass


def _run_with_time_bound(seconds: int, func, *args):
    """Run func(*args); fail with _Hang if it takes longer than `seconds` (Unix only; elsewhere no bound).

    Pyodide (WebAssembly) defines signal.SIGALRM but has no signal.alarm, so both must be there."""
    if not (hasattr(signal, "SIGALRM") and hasattr(signal, "alarm")):
        return func(*args)

    def _on_alarm(signum, frame):
        raise _Hang(f"did not finish in {seconds} s")

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(seconds)
    try:
        return func(*args)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _make_shot() -> Shot:
    dm = DragModel(0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24))
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.05)),
        ammo=Ammo(dm, Velocity.MPS(800)),
        look_angle=Angular.Degree(LOOK_DEG),
    )


@pytest.mark.parametrize("min_altitude_ft", MIN_ALTITUDES_FT)
def test_range_limit_wins_over_altitude_limit_in_the_same_step(loaded_engine_instance, min_altitude_ft):
    """The rows are the start and the row at the range limit; no extra row after it and no RangeError."""
    x_ft = TARGET_M / 0.3048 * math.cos(math.radians(LOOK_DEG))  # ~2.863 ft: the range limit in x
    engine = loaded_engine_instance(BaseEngineConfigDict(cMinimumAltitude=min_altitude_ft))
    shot = _make_shot()
    shot.barrel_elevation = Angular.Radian(BARREL_RAD)
    hit = engine.integrate(shot, Distance.Foot(x_ft), Distance.Foot(x_ft), filter_flags=TrajFlag.RANGE)
    assert hit.error is None
    assert len(hit.records) == 2, [(r.flag, r.time, r.distance >> Distance.Foot) for r in hit.records]
    assert hit.records[0].time == 0.0
    last = hit.records[-1]
    assert last.flag & TrajFlag.RANGE
    assert last.distance >> Distance.Foot == pytest.approx(x_ft, abs=1e-9)


@pytest.mark.parametrize("min_altitude_ft", (-1641.0,))
def test_limit_before_the_range_limit_still_ends_the_shot(loaded_engine_instance, min_altitude_ft):
    """A shot that hits the altitude limit before it reaches the range limit is unchanged: RangeError, last row = step end."""
    x_ft = TARGET_M / 0.3048 * math.cos(math.radians(LOOK_DEG))
    engine = loaded_engine_instance(BaseEngineConfigDict(cMinimumAltitude=min_altitude_ft))
    shot = _make_shot()
    shot.barrel_elevation = Angular.Radian(BARREL_RAD)
    hit = engine.integrate(shot, Distance.Foot(10 * x_ft), Distance.Foot(10 * x_ft), filter_flags=TrajFlag.RANGE)
    assert isinstance(hit.error, RangeError)
    assert hit.records[-1].distance >> Distance.Foot < 10 * x_ft


def test_near_vertical_downhill_zero_returns_and_hits(loaded_engine_instance):
    """zero_angle of the look -89.9 degree, 500 m shot returns at once (it did not in 600 s) and the shot hits."""
    calc = Calculator(engine=loaded_engine_instance)
    shot = _make_shot()
    angle = _run_with_time_bound(30, calc.zero_angle, shot, Distance.Meter(TARGET_M))
    shot.relative_angle = angle - shot.look_angle
    horizontal_m = TARGET_M * math.cos(math.radians(LOOK_DEG))
    # (fired with the limits lifted: at the default altitude limit of -1500 ft the shot itself stops short of 500 m below)
    fire_calc = Calculator(
        config=BaseEngineConfigDict(cMaximumDrop=-40000.0, cMinimumAltitude=-40000.0), engine=loaded_engine_instance
    )
    point = fire_calc.fire(shot, Distance.Meter(horizontal_m), flags=TrajFlag.RANGE, raise_range_error=False)[-1]
    assert point.slant_distance >> Distance.Meter == pytest.approx(TARGET_M, abs=1e-3)
    assert abs(point.slant_height >> Distance.Foot) < 1e-4
