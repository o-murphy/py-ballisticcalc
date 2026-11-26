"""The exact cant model of `Shot` (C37) and the solvers that work in it.

The barrel is pitched by `r = zero_elevation + relative_angle` in the sight plane, which is rotated about the line of
sight by the cant.  In the frame of the line of sight (x forward, y up, z right) its direction is
`(cos r, sin r cos c, sin r sin c)`; the look angle `L` then rotates that frame about z into the world.
"""

import math

import pytest

from py_ballisticcalc import Calculator
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot, ShotProps
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *
from tests.repin_xfail import xfail_until_cant_repin

CANTS = (0.0, 10.0, 45.0)
LOOKS = (0.0, 5.0)


def _make_shot(cant_deg: float, look_deg: float = 0.0, sight_height: Distance | None = None, mv_mps: float = 800.0):
    return Shot(
        weapon=Weapon(sight_height=sight_height or Distance.Inch(2), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(mv_mps)),
        look_angle=Angular.Degree(look_deg),
        cant_angle=Angular.Degree(cant_deg),
    )


def _direction_in_world(look: float, cant: float, pitch: float) -> tuple[float, float, float]:
    """Independent computation: the unit vector of the barrel, by rotating vectors (x forward, y up, z right)."""
    # Barrel in the sight plane at pitch r: rotate x about the (unrolled) z axis by r ...
    x, y, z = math.cos(pitch), math.sin(pitch), 0.0
    # ... then roll the sight plane about the line of sight (x axis) by the cant ...
    y, z = y * math.cos(cant) - z * math.sin(cant), y * math.sin(cant) + z * math.cos(cant)
    # ... and tilt the line of sight up by the look angle (about z).
    return x * math.cos(look) - y * math.sin(look), x * math.sin(look) + y * math.cos(look), z


@pytest.mark.parametrize("cant_deg", (0.0, 10.0, 45.0, -30.0, 80.0))
@pytest.mark.parametrize("look_deg", (0.0, 5.0, -12.0))
@pytest.mark.parametrize("pitch_deg", (0.3, 1.5, -0.4, 20.0))
def test_barrel_direction_matches_closed_form(cant_deg, look_deg, pitch_deg):
    shot = _make_shot(cant_deg, look_deg)
    shot.relative_angle = Angular.Degree(pitch_deg)
    x, y, z = _direction_in_world(math.radians(look_deg), math.radians(cant_deg), math.radians(pitch_deg))
    assert shot.barrel_elevation >> Angular.Radian == pytest.approx(math.atan2(y, math.hypot(x, z)), abs=1e-14)
    assert shot.barrel_azimuth >> Angular.Radian == pytest.approx(math.atan2(z, x), abs=1e-14)


@pytest.mark.parametrize("look_deg", (0.0, 5.0, -5.0))
def test_no_cant_reduces_exactly(look_deg):
    """With cant = 0: elevation is look + pitch and azimuth is zero, bit for bit."""
    shot = _make_shot(0.0, look_deg)
    shot.weapon.zero_elevation = Angular.Mil(1.7)
    shot.relative_angle = Angular.Degree(-0.37)
    look = shot.look_angle >> Angular.Radian
    pitch = (shot.weapon.zero_elevation >> Angular.Radian) + (shot.relative_angle >> Angular.Radian)
    assert (shot.barrel_elevation >> Angular.Radian) == look + pitch
    assert (shot.barrel_azimuth >> Angular.Radian) == 0.0
    props = ShotProps.from_shot(shot)
    assert props.barrel_elevation_rad == look + pitch
    props.set_aim(0.123)  # the solvers' unknown is the elevation itself; the azimuth is untouched
    assert (props.barrel_elevation_rad, props.barrel_azimuth_rad) == (0.123, 0.0)


@pytest.mark.parametrize("cant_deg", CANTS)
@pytest.mark.parametrize("look_deg", LOOKS)
@pytest.mark.parametrize("zero_mil", (0.0, 1.5))
def test_setter_getter_round_trip(cant_deg, look_deg, zero_mil):
    shot = _make_shot(cant_deg, look_deg)
    shot.weapon.zero_elevation = Angular.Mil(zero_mil)
    for elevation_deg in (look_deg + 1.1, look_deg - 0.8, 0.7, 12.0):
        shot.barrel_elevation = Angular.Degree(elevation_deg)
        assert shot.barrel_elevation >> Angular.Degree == pytest.approx(elevation_deg, abs=1e-12 * 57.3)


@pytest.mark.parametrize("cant_deg", (10.0, 45.0, 60.0))
@pytest.mark.parametrize("look_deg", LOOKS)
def test_unreachable_elevation_raises(cant_deg, look_deg):
    """The elevation of a canted barrel is limited to asin(R), R = hypot(sin L, cos L cos c)."""
    look, cant = math.radians(look_deg), math.radians(cant_deg)
    limit = math.asin(math.hypot(math.sin(look), math.cos(look) * math.cos(cant)))
    shot = _make_shot(cant_deg, look_deg)
    shot.barrel_elevation = Angular.Radian(limit * 0.999)  # reachable
    with pytest.raises(ValueError, match="not reachable"):
        shot.barrel_elevation = Angular.Radian(limit * 1.001)
    with pytest.raises(ValueError, match="not reachable"):
        shot.barrel_elevation = Angular.Degree(89.0)


def test_unreachable_elevation_does_not_change_the_shot():
    shot = _make_shot(45.0)
    shot.relative_angle = Angular.Degree(0.5)
    with pytest.raises(ValueError):
        shot.barrel_elevation = Angular.Degree(60)
    assert shot.relative_angle >> Angular.Degree == pytest.approx(0.5, abs=1e-12)


def test_props_set_aim_clamps_unreachable_elevation():
    """A solver may probe an elevation beyond the limit: it is clamped, not raised."""
    props = ShotProps.from_shot(_make_shot(45.0))
    props.set_aim(math.radians(80))
    assert props.aim_elevation_rad == math.radians(80)
    assert props.barrel_elevation_rad == pytest.approx(math.radians(45.0), abs=1e-12)
    props.set_aim(math.radians(10))
    assert props.barrel_elevation_rad == pytest.approx(math.radians(10), abs=1e-12)
    assert props.barrel_azimuth_rad > 0


@pytest.mark.parametrize("cant_deg", (10.0, 45.0))
def test_small_cant_differs_from_scaled_pitch_by_less_than_1e_4_degrees(cant_deg):
    """Magnitude of the change from the former `look + cos(cant) * r`: tiny for an ordinary shot (r about 0.1 deg)."""
    shot = _make_shot(cant_deg)
    shot.relative_angle = Angular.Degree(0.1)
    old = math.cos(math.radians(cant_deg)) * math.radians(0.1)
    assert abs((shot.barrel_elevation >> Angular.Radian) - old) < math.radians(1e-4)


# region solvers


def _fire_miss_ft(calc: Calculator, shot: Shot, distance: Distance) -> tuple[float, float]:
    """Height above the line of sight and windage (feet) at the slant `distance`."""
    horizontal = Distance.Foot((distance >> Distance.Foot) * math.cos(shot.look_angle >> Angular.Radian))
    point = calc.fire(shot, horizontal, flags=TrajFlag.RANGE, raise_range_error=False)[-1]
    return point.slant_height >> Distance.Foot, point.windage >> Distance.Foot


def _kind(engine) -> str:
    module = getattr(engine, "__module__", "") or ""
    for key in ("scipy", "euler", "rk4", "velocity_verlet"):
        if module.startswith("py_ballisticcalc.engines.") and key in module:
            return key
    return "other"


@pytest.mark.slow
@pytest.mark.engine
@pytest.mark.parametrize("look_deg", LOOKS)
def test_lofted_zero_with_cant_hits_in_height(request, loaded_engine_instance, look_deg):
    """A lofted zero with a cant hits the line of sight in height (and drifts sideways: windage is a result)."""
    kind = _kind(loaded_engine_instance)
    if kind not in ("rk4", "scipy"):
        pytest.skip("lofted zero is slow; checked on RK4 and SciPy")
    xfail_until_cant_repin(request, loaded_engine_instance)
    shot = _make_shot(10.0, look_deg, Distance.Meter(0.05))
    config = BaseEngineConfigDict(cMinimumVelocity=0.0, cMaximumDrop=-60000.0, cMinimumAltitude=-60000.0)
    calc = Calculator(config=config, engine=loaded_engine_instance)
    distance = Distance.Meter(300)
    elevation = calc._engine_instance.find_zero_angle(shot, distance, lofted=True)
    shot.barrel_elevation = elevation
    miss_ft, windage_ft = _fire_miss_ft(calc, shot, distance)
    # SciPy's adaptive integrator over a minute of flight is CPU/platform dependent (misses of 2.5-5.9 mm measured on
    # Linux, macOS and Windows), so it gets a wider bound than the fixed-step Python engines.
    tolerance_m = 1e-2 if kind == "scipy" else 1e-3
    assert miss_ft * 0.3048 == pytest.approx(0.0, abs=tolerance_m)
    assert abs(windage_ft) > 1.0  # the canted lofted shot lands well to the side; nothing constrains it


@pytest.mark.engine
@pytest.mark.parametrize("cant_deg", (10.0, 60.0))
@pytest.mark.parametrize(("sight_m", "look_deg"), ((0.05, 0.0), (0.5, 0.0), (0.5, 10.0)))
@pytest.mark.parametrize("distance_m", (0.05, 0.1, 0.2))
def test_close_target_zero_with_cant(request, loaded_engine_instance, cant_deg, sight_m, look_deg, distance_m):
    """The very close shot shortcut follows the exact model: the bore is offset sideways by `h sin(cant)`."""
    xfail_until_cant_repin(request, loaded_engine_instance)
    h, d, look, cant = sight_m, distance_m, math.radians(look_deg), math.radians(cant_deg)
    shortcut = d < 2.0 * h * math.cos(cant)  # the calc step (cStepMultiplier, 0.0025 ft) is smaller
    if not shortcut and _kind(loaded_engine_instance) in ("rk4", "euler", "velocity_verlet"):
        pytest.skip("searched zero is too slow on pure-Python engines; the shortcut cases cover the change")
    shot = _make_shot(cant_deg, look_deg, Distance.Meter(sight_m))
    calc = Calculator(engine=loaded_engine_instance)
    elevation = calc._engine_instance.find_zero_angle(shot, Distance.Meter(distance_m))
    pitch = math.atan2(h * math.cos(look), d + h * math.cos(cant) * math.sin(look))
    if shortcut:
        x, y, z = _direction_in_world(look, cant, pitch)
        assert elevation >> Angular.Radian == pytest.approx(math.atan2(y, math.hypot(x, z)), abs=1e-12)
    # The pitch is reachable as a barrel elevation only up to pi/2 - phi, phi = atan2(sin L, cos L cos c).  A very high
    # sight on a steep cant needs more (the elevation has no pitch to aim back): the call has answered, nothing can hit.
    if pitch > math.pi / 2 - math.atan2(math.sin(look), math.cos(look) * math.cos(cant)) + 1e-9:
        assert math.isfinite(elevation >> Angular.Radian)
        return
    shot.barrel_elevation = elevation
    miss_ft, _ = _fire_miss_ft(calc, shot, Distance.Meter(distance_m))
    # SciPy results are CPU/platform dependent: wider bound.
    assert miss_ft * 0.3048 == pytest.approx(0.0, abs=1e-2 if _kind(loaded_engine_instance) == "scipy" else 2e-3)


# endregion
