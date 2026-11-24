"""Edge cases of the zero search that are documented behaviour (classes C15, C20, C21 of the differential run).

* A zero distance shorter than 0.01 ft is not aimed: the look angle is returned (it misses the line of sight by the sight
  height; the zero cannot be measured that close).  `find_zero_point` has no trajectory point to return then.
* A negative zero distance is not supported (aim backwards with the look angle): `ZeroFindingError`.
* Cant is part of the shot: the sight height is rotated by it and the solver keeps the shot's barrel azimuth.  The
  returned angle is the barrel elevation for that shot: firing it with the same shot hits the line of sight at the target.
"""

import math

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.exceptions import SolverRuntimeError, ZeroFindingError
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

# The firing check is geometric, so the tolerance is the solver's own: the measured miss is below 3e-7 ft on every engine
# (Ridder/Newton stop at cZeroFindingAccuracy = 5e-6 ft), so 1e-4 ft holds with a margin of more than two orders.
HEIGHT_TOLERANCE_FT = 1e-4


def _make_shot(cant_deg: float = 0.0, look_deg: float = 0.0) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Inch(2), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(800)),
        look_angle=Angular.Degree(look_deg),
        cant_angle=Angular.Degree(cant_deg),
    )


def _slant_height_at_target_ft(calc: Calculator, shot: Shot, elevation: Angular, distance: Distance) -> float:
    """Fire `shot` with barrel elevation `elevation` (vertical plane, from horizontal); return the miss of the line of sight."""
    cant = shot.cant_angle >> Angular.Radian
    shot.weapon.zero_elevation = Angular.Radian(0)
    # Shot applies relative_angle scaled by cos(cant): undo it to fire exactly `elevation`.
    shot.relative_angle = Angular.Radian(((elevation - shot.look_angle) >> Angular.Radian) / math.cos(cant))
    horizontal = Distance.Foot((distance >> Distance.Foot) * math.cos(shot.look_angle >> Angular.Radian))
    result = calc.fire(shot, horizontal, flags=TrajFlag.RANGE, raise_range_error=False)
    point = result[-1]
    assert point.slant_distance >> Distance.Foot == pytest.approx(distance >> Distance.Foot, abs=1e-3)
    return point.slant_height >> Distance.Foot


# region C20: zero distance shorter than 0.01 ft


@pytest.mark.parametrize("distance_ft", (0.0, 0.005, -0.005))
@pytest.mark.parametrize("function", ("zero_angle", "find_zero_angle"))
@pytest.mark.parametrize("look_deg", (0.0, 5.0))
def test_zero_too_close_returns_look_angle(loaded_engine_instance, function, distance_ft, look_deg):
    """Below 0.01 ft (feet, whatever the preferred units) the look angle is returned: the shot is not aimed."""
    shot = _make_shot(look_deg=look_deg)
    engine = Calculator(engine=loaded_engine_instance)._engine_instance
    angle = getattr(engine, function)(shot, Distance.Foot(distance_ft))
    assert angle >> Angular.Radian == pytest.approx(look_deg * math.pi / 180.0, abs=1e-12)


def test_zero_too_close_threshold_is_in_feet(loaded_engine_instance):
    """0.005 ft is too close however it is expressed; 0.005 m (0.0164 ft) is a (geometric) close target, which is aimed."""
    shot = _make_shot()
    engine = Calculator(engine=loaded_engine_instance)._engine_instance
    assert engine.zero_angle(shot, Distance.Inch(0.05)) >> Angular.Radian == 0.0  # 0.0042 ft
    aimed = engine.zero_angle(shot, Distance.Meter(0.005))
    assert aimed >> Angular.Degree > 0  # straight line from the bore (2 in below the sight) to the target


def test_find_zero_point_too_close_has_no_point(loaded_engine_instance):
    """No trajectory is evaluated for a zero that close, so `find_zero_point` raises `SolverRuntimeError`."""
    shot = _make_shot()
    engine = Calculator(engine=loaded_engine_instance)._engine_instance
    with pytest.raises(SolverRuntimeError):
        engine.find_zero_point(shot, Distance.Foot(0.005))


def test_set_weapon_zero_too_close(loaded_engine_instance):
    """`set_weapon_zero` stores a zero elevation of 0 (relative to the look angle) for a distance below 0.01 ft."""
    shot = _make_shot(look_deg=5.0)
    calc = Calculator(engine=loaded_engine_instance)
    assert calc.set_weapon_zero(shot, Distance.Foot(0.005)) >> Angular.Radian == 0.0


# endregion C20

# region C15: negative distance


@pytest.mark.parametrize("function", ("zero_angle", "find_zero_angle", "find_zero_point"))
def test_negative_zero_distance_raises(loaded_engine_instance, function):
    """A negative distance is not supported (aim backwards with the look angle); the Python and native engines agree."""
    shot = _make_shot()
    engine = Calculator(engine=loaded_engine_instance)._engine_instance
    with pytest.raises(ZeroFindingError):
        getattr(engine, function)(shot, Distance.Foot(-10))


# endregion C15

# region C21: cant


@pytest.mark.parametrize("cant_deg", (10.0, 45.0))
@pytest.mark.parametrize("function", ("zero_angle", "find_zero_angle"))
def test_zero_with_cant_hits_target(loaded_engine_instance, function, cant_deg):
    """The zero of a canted shot, fired with the same shot, crosses the line of sight at the target."""
    shot = _make_shot(cant_deg)
    calc = Calculator(engine=loaded_engine_instance)
    distance = Distance.Yard(100)
    elevation = getattr(calc._engine_instance, function)(shot, distance)
    assert _slant_height_at_target_ft(calc, shot, elevation, distance) == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_FT)


@pytest.mark.parametrize("cant_deg", (10.0, 45.0))
def test_zero_with_cant_differs_from_no_cant(loaded_engine_instance, cant_deg):
    """The sight height is rotated by the cant, so the canted zero needs less elevation than the upright one."""
    calc = Calculator(engine=loaded_engine_instance)
    distance = Distance.Yard(100)
    upright = calc._engine_instance.zero_angle(_make_shot(0.0), distance) >> Angular.Radian
    canted = calc._engine_instance.zero_angle(_make_shot(cant_deg), distance) >> Angular.Radian
    assert canted < upright


# endregion C21
