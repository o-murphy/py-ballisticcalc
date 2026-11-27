"""Cant is applied consistently by `Shot`, `Calculator.set_weapon_zero` and the aiming helpers.

`Shot.barrel_elevation` is the exact elevation of the pitch `zero_elevation + relative_angle` in the canted sight plane
(see `tests/test_cant_exact.py`); its setter and `set_weapon_zero` are exact inverses of it, so the elevation that was
asked for is the elevation that is fired.
"""

import math

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

HEIGHT_TOLERANCE_FT = 1e-4
CANTS = (0.0, 10.0, 45.0)
LOOKS = (0.0, 5.0)


def _make_shot(cant_deg: float, look_deg: float, zero_elevation: Angular | None = None) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Inch(2), twist=Distance.Inch(11), zero_elevation=zero_elevation),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(800)),
        look_angle=Angular.Degree(look_deg),
        cant_angle=Angular.Degree(cant_deg),
    )


@pytest.mark.parametrize("cant_deg", CANTS)
@pytest.mark.parametrize("look_deg", LOOKS)
@pytest.mark.parametrize("zero_mil", (0.0, 1.5))
def test_barrel_elevation_setter_is_inverse_of_getter(cant_deg, look_deg, zero_mil):
    shot = _make_shot(cant_deg, look_deg, Angular.Mil(zero_mil))
    for value in (Angular.Degree(0.7), Angular.Degree(-0.3), Angular.Degree(look_deg + 1.1)):
        shot.barrel_elevation = value
        assert (shot.barrel_elevation >> Angular.Radian) == pytest.approx(value >> Angular.Radian, abs=1e-12)


def test_barrel_elevation_setter_rejects_cant_of_90_degrees():
    shot = _make_shot(90.0, 0.0)
    with pytest.raises(ValueError, match="cant"):
        shot.barrel_elevation = Angular.Degree(1)


@pytest.mark.parametrize("cant_deg", CANTS)
@pytest.mark.parametrize("look_deg", LOOKS)
def test_set_weapon_zero_fires_the_solved_elevation(request, loaded_engine_instance, cant_deg, look_deg):
    calc = Calculator(engine=loaded_engine_instance)
    shot = _make_shot(cant_deg, look_deg)
    distance = Distance.Yard(100)
    # `barrel_elevation_for_target` is relative to the look angle.
    expected = (calc.barrel_elevation_for_target(shot, distance) >> Angular.Radian) + (
        shot.look_angle >> Angular.Radian
    )
    calc.set_weapon_zero(shot, distance)
    assert (shot.barrel_elevation >> Angular.Radian) == pytest.approx(expected, abs=1e-12)
    # and the trajectory fired with the shot as is crosses the line of sight at the zero distance
    horizontal = Distance.Foot((distance >> Distance.Foot) * math.cos(look_deg * math.pi / 180))
    point = calc.fire(shot, horizontal, flags=TrajFlag.RANGE, raise_range_error=False)[-1]
    assert point.slant_distance >> Distance.Foot == pytest.approx(distance >> Distance.Foot, abs=1e-3)
    assert point.slant_height >> Distance.Foot == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_FT)


@pytest.mark.parametrize("cant_deg", (10.0, 45.0))
def test_aim_hold_hits_target(request, loaded_engine_instance, cant_deg):
    """The hold of `aim` is the `relative_angle` that fires the solved elevation."""
    calc = Calculator(engine=loaded_engine_instance)
    shot = _make_shot(cant_deg, 5.0)
    calc.set_weapon_zero(shot, Distance.Yard(100))
    target = Distance.Yard(300)
    expected = (calc.barrel_elevation_for_target(shot, target) >> Angular.Radian) + (shot.look_angle >> Angular.Radian)
    hold, _, _ = calc.aim(shot, target)
    shot.relative_angle = hold
    assert (shot.barrel_elevation >> Angular.Radian) == pytest.approx(expected, abs=1e-7)  # solver tolerance


def test_set_weapon_zero_rejects_cant_of_90_degrees(loaded_engine_instance):
    calc = Calculator(engine=loaded_engine_instance)
    shot = _make_shot(90.0, 0.0)
    with pytest.raises(ValueError, match="cant"):
        calc.set_weapon_zero(shot, Distance.Yard(100))


def test_cant_zero_is_unchanged(loaded_engine_instance):
    """With no cant the pitch is the look-relative elevation exactly: the stored zero is the solver's angle relative to the look angle, bit for bit."""
    calc = Calculator(engine=loaded_engine_instance)
    shot = _make_shot(0.0, 5.0)
    distance = Distance.Yard(100)
    relative = calc.barrel_elevation_for_target(shot, distance)
    stored = calc.set_weapon_zero(shot, distance)
    assert (stored >> Angular.Radian) == (relative >> Angular.Radian)
