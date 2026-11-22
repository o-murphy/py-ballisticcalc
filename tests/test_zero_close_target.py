"""Zero angle of very close targets.

For a target closer than about twice the sight height the zero finder returns a straight-line angle (no search,
"ignore gravity and drag").  The line goes from the bore, which is `sight_height` BELOW the line of sight at the
shooter, up to the target on the line of sight; so the angle must be positive for a sight above the bore.
A wrong sign makes the bore point away from the line of sight and misses it by twice the sight height.
"""

import math

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

CLOSE_TARGETS_M = (0.05, 0.1, 0.2, 0.4, 0.6, 0.9, 1.0)
SIGHT_HEIGHTS_M = (0.05, 0.1, 0.5)
VELOCITIES_MPS = (300.0, 800.0)

# Bullet height above the line of sight at the target, in meters.  Gravity and drag over a meter are
# negligible (< 0.1 mm), so the zero shot must be on the line of sight up to the solver tolerance.
HEIGHT_TOLERANCE_M = 2e-3


def _make_shot(sight_height_m: float, mv_mps: float, drag_table=TableG7) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(sight_height_m), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, drag_table), Velocity.MPS(mv_mps)),
    )


def _fire_with_zero(calc: Calculator, shot: Shot, zero_angle: Angular, distance_m: float):
    """Fire `shot` with `zero_angle` as its relative angle; return the RANGE point at the target.

    `distance_m` is the slant distance to the target; the trajectory range is its horizontal projection.
    """
    shot.relative_angle = zero_angle
    horizontal_m = distance_m * math.cos(shot.look_angle >> Angular.Radian)
    result = calc.fire(shot, Distance.Meter(horizontal_m), flags=TrajFlag.RANGE, raise_range_error=False)
    point = result[-1]
    assert point.slant_distance >> Distance.Meter == pytest.approx(distance_m, abs=1e-3)
    return point


@pytest.mark.parametrize("velocity", VELOCITIES_MPS)
@pytest.mark.parametrize("sight_height", SIGHT_HEIGHTS_M)
@pytest.mark.parametrize("distance", CLOSE_TARGETS_M)
def test_close_target_zero_hits_line_of_sight(loaded_engine_instance, distance, sight_height, velocity):
    """The zero shot of a close target crosses the line of sight at the target."""
    shot = _make_shot(sight_height, velocity)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance))

    # The bore is below the sight line at the shooter, so it must point up to reach it.
    assert angle >> Angular.Degree > 0
    point = _fire_with_zero(calc, shot, angle, distance)
    assert point.slant_height >> Distance.Meter == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)


@pytest.mark.parametrize("distance", (0.1, 0.4, 0.9))
@pytest.mark.parametrize("sight_height", (0.1, 0.5))
def test_close_target_zero_angle_is_straight_line(loaded_engine_instance, distance, sight_height):
    """With drag and gravity negligible the zero angle is the line from the bore to the target."""
    shot = _make_shot(sight_height, 800.0)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance))
    # Straight line from (0, -sight_height) to (distance, 0); gravity/drag over < 1 m shift it by < 0.05 deg.
    expected = math.degrees(math.atan2(sight_height, distance))
    assert angle >> Angular.Degree == pytest.approx(expected, abs=0.05)


# Slow on pure-Python engines (the zero point is searched for, not computed), so a few cases only.
@pytest.mark.parametrize("sight_height", (0.1, 0.5))
@pytest.mark.parametrize("distance", (0.2, 0.9))
def test_close_target_zero_point(loaded_engine_instance, distance, sight_height):
    """find_zero_point (where implemented) agrees in sign and magnitude with find_zero_angle."""
    shot = _make_shot(sight_height, 800.0)
    calc = Calculator(engine=loaded_engine_instance)
    engine = calc._engine_instance
    if not hasattr(engine, "find_zero_point"):
        pytest.skip("engine does not implement find_zero_point")
    angle = engine.find_zero_angle(shot, Distance.Meter(distance))
    try:
        point_angle, point = engine.find_zero_point(shot, Distance.Meter(distance))
    except Exception as error:  # fast-path zeros integrate nothing, so there is no point to return
        if type(error).__name__ != "SolverRuntimeError":
            raise
        pytest.skip("zero fast path has no trajectory point")
    assert point_angle >> Angular.Degree > 0
    assert point_angle >> Angular.Degree == pytest.approx(angle >> Angular.Degree, abs=1e-3)
    assert point.slant_height >> Distance.Meter == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)


@pytest.mark.parametrize("look_angle", (-10.0, 15.0, 45.0))
@pytest.mark.parametrize("sight_height", (0.1, 0.5))
@pytest.mark.parametrize("distance", (0.2, 0.4, 0.9))
def test_close_target_zero_with_look_angle(loaded_engine_instance, distance, sight_height, look_angle):
    """With a look angle the zero shot reaches the (slant) line of sight at the target."""
    shot = _make_shot(sight_height, 800.0, TableG1)
    shot.look_angle = Angular.Degree(look_angle)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance))

    # The bore points above the line of sight (elevation is measured from horizontal; look angle included).
    assert angle >> Angular.Degree > look_angle
    point = _fire_with_zero(calc, shot, angle - shot.look_angle, distance)
    assert point.slant_height >> Distance.Meter == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)


@pytest.mark.parametrize("distance", (0.2, 0.4, 0.9))
def test_close_target_zero_with_cant(loaded_engine_instance, distance):
    """A canted rifle has an effective sight height of sight_height*cos(cant); the zero follows it."""
    sight_height = 0.1
    shot = _make_shot(sight_height, 800.0)
    shot.cant_angle = Angular.Degree(30)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance))
    expected = math.degrees(math.atan2(sight_height * math.cos(math.radians(30)), distance))
    assert angle >> Angular.Degree == pytest.approx(expected, abs=0.05)
