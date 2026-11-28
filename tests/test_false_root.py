"""A lofted zero search must not report a jump of the error function as a root.

The miss at a target (`height - |range error|`) is not continuous for a lofted shot near the vertical: a shot that falls
back short of the target and one that carries past it differ by thousands of feet, and the same elevation can be on
either side of the jump.  A bracket of the search that holds such a jump has a sign change that is not a zero, and
Ridder's method (and `brentq`) converge on it all the same: the angle tolerance is met, the search "succeeds" and returns
an angle that does not reach the target.  `find_zero_angle` / `find_zero_point` now raise `ZeroFindingError` when the error
at the converged angle is comparable to the bracket-end errors (see `BaseIntegrationEngine._require_continuous_root`).

The reported case: 175 gr G7 .308, 800 m/s, 5 m/s tail wind, 100 m zero, lofted: the search converged on 88.4362 deg,
where the error jumps from +8700 ft to -1600 ft, and a shot fired there never reaches 328 ft (it falls 1300 ft short).
"""

import math

import pytest

from py_ballisticcalc import BaseEngineConfigDict, Calculator, ZeroFindingError
from py_ballisticcalc.conditions import Wind
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

ANGLE_TOLERANCE_RAD = 1e-9
# SciPy's adaptive solve_ivp + brentq zero differs by 1e-9..4e-8 rad between CPUs/libm (observed in CI against the values
# recorded locally), so its recorded elevations are compared to 1e-6 rad; the pure-Python engines are deterministic floats.
SCIPY_ANGLE_TOLERANCE_RAD = 1e-6
# Height above the line of sight at the target (m) for a zero that is a real root (as in the other zero tests).
HEIGHT_TOLERANCE_M = 2e-3


def _kind(engine) -> str:
    module = getattr(engine, "__module__", "") or ""
    for key in ("scipy", "euler", "rk4", "velocity_verlet"):
        if module.startswith("py_ballisticcalc.engines.") and key in module:
            return key
    return "other"


def _is_pure_python(engine) -> bool:
    return _kind(engine) in ("euler", "rk4", "velocity_verlet")


def _make_shot(winds=(), cant_deg: float = 0.0) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.05), twist=Distance.Inch(11)),
        ammo=Ammo(
            DragModel(
                0.31, TableG7, weight=Weight.Grain(175), diameter=Distance.Inch(0.308), length=Distance.Inch(1.24)
            ),
            Velocity.MPS(800),
        ),
        winds=[
            Wind(Velocity.MPS(v), Angular.Degree(direction), Distance.Meter(until)) for v, direction, until in winds
        ],
        cant_angle=Angular.Degree(cant_deg),
    )


TAIL_WIND = ((5.0, 180.0, 3000.0),)
CROSS_WIND = ((5.0, 90.0, 3000.0),)


@pytest.mark.parametrize("method", ("find_zero_angle", "find_zero_point"))
def test_lofted_zero_at_a_discontinuity_raises(request, loaded_engine_instance, method):
    """The only sign change of the lofted bracket is the jump: ZeroFindingError, not an angle that misses by 1300 ft."""
    if _kind(loaded_engine_instance) == "other" and not (getattr(loaded_engine_instance, "__module__", "") or "").startswith(("py_ballisticcalc_exts", "tiny_bclibc")):
        pytest.skip("unknown engine")
    if getattr(loaded_engine_instance, "__module__", "").startswith("tiny_bclibc"):
        pytest.skip("tiny_bclibc has no lofted search")
    engine = loaded_engine_instance({})
    with pytest.raises(ZeroFindingError, match="No continuous lofted zero") as excinfo:
        getattr(engine, method)(_make_shot(TAIL_WIND), Distance.Meter(100), lofted=True)
    error = excinfo.value
    # The error carries the evidence: the elevation the search ended on (near the jump) and its error, thousands of feet.
    assert error.last_barrel_elevation >> Angular.Degree == pytest.approx(88.4362, abs=0.01)
    assert error.zero_finding_error > 1000.0


def test_discontinuity_does_not_affect_the_low_zero(loaded_engine_instance):
    """The same shot has a low zero: only the lofted search is refused."""
    if getattr(loaded_engine_instance, "__module__", "").startswith("tiny_bclibc"):
        pytest.skip("tiny_bclibc has no lofted search")
    if _is_pure_python(loaded_engine_instance) and _kind(loaded_engine_instance) != "rk4":
        pytest.skip("covered by the rk4 engine")
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(_make_shot(TAIL_WIND), Distance.Meter(100))
    assert 0.0 < angle >> Angular.Degree < 1.0


def test_continuous_root_test_is_scale_free(loaded_engine_instance):
    """`|f(root)| <= ratio * min(|f(low)|, |f(high)|)` passes, anything larger raises; the scale of the errors is free."""
    if not hasattr(loaded_engine_instance, "_require_continuous_root"):
        pytest.skip("pure-Python helper")
    engine = loaded_engine_instance({})
    ratio = engine.CONTINUOUS_ROOT_RATIO
    assert 0.1 < ratio < 2.0  # between the measured real roots (<= 0.1, SciPy) and jumps (>= 2.0), not on either
    for scale in (1e-3, 1.0, 1e4):
        low, high = 3.0 * scale, -40.0 * scale  # the smaller bracket-end error is the first
        engine._require_continuous_root(0.99 * ratio * low, (low, high), 1.5, 7, True)
        engine._require_continuous_root(-0.99 * ratio * low, (high, low), 1.5, 7, True)
        for root_error in (1.01 * ratio * low, -1.01 * ratio * low, low, 5.0 * high):
            with pytest.raises(ZeroFindingError, match="No continuous lofted zero") as excinfo:
                engine._require_continuous_root(root_error, (low, high), 1.5, 7, True)
            assert excinfo.value.iterations_count == 7
            assert excinfo.value.last_barrel_elevation >> Angular.Radian == 1.5
    with pytest.raises(ZeroFindingError, match="No continuous low zero"):
        engine._require_continuous_root(1.0, (2.0, -2.0), 0.01, 3, False)


# Lofted zeros that are real roots (the error function is continuous there) and their elevations before the check:
# they must come out unchanged.  Two of them (`cant300`, `tail500`) end on the bracket collapse, the exit that is checked.
LEGIT_CASES = {  # name: (distance m, winds, cant degrees)
    "d50": (50.0, (), 0.0),
    "d100": (100.0, (), 0.0),
    "d300": (300.0, (), 0.0),
    "d1000": (1000.0, (), 0.0),
    "cross300": (300.0, CROSS_WIND, 0.0),
    "cant300": (300.0, (), 10.0),
    "tail500": (500.0, TAIL_WIND, 0.0),
}
# Elevations (radians) recorded before the discontinuity check, per engine.  `cant300` is the elevation in the exact canted
# model (C37; it was 1.5431 rad = 88.4 deg with the old scaling): it hits the line of sight in height like the others.
LEGIT_ANGLES = {
    "rk4": {
        "d50": 1.5661788498467573,
        "d100": 1.5615601782246449,
        "d300": 1.5430550710767825,
        "d1000": 1.4773083610653304,
        "cross300": 1.543053139488336,
        "cant300": 1.3939553458072833,
        "tail500": 1.5044424365315816,
    },
    "scipy": {
        "d50": 1.566179194587697,
        "d100": 1.5615608804888108,
        "d300": 1.5430572062553463,
        "d1000": 1.4773156165940016,
        "cross300": 1.5430552473775156,
        "cant300": 1.3939556864233822,
        "tail500": 1.504446842777301,
    },
    "euler": {"d100": 1.561559495804815, "d300": 1.5430532364867933, "cant300": 1.3939551100166225},
    "velocity_verlet": {"d100": 1.5615606919146785, "d300": 1.543056615865713, "cant300": 1.3939555943949697},
}


def _legit_params():
    return [(kind, name) for kind, angles in LEGIT_ANGLES.items() for name in angles]


def _height_miss_m(calc: Calculator, shot: Shot, angle: Angular, distance_m: float) -> float:
    shot.barrel_elevation = angle
    result = calc.fire(shot, Distance.Meter(distance_m), flags=TrajFlag.RANGE, raise_range_error=False)
    point = result[-1]
    assert point.distance >> Distance.Meter == pytest.approx(distance_m, abs=1e-3)
    return point.slant_height >> Distance.Meter


@pytest.mark.slow
@pytest.mark.parametrize(("kind", "name"), _legit_params())
def test_real_lofted_zeros_are_unchanged(loaded_engine_instance, kind, name):
    """Lofted zeros that are real roots still return their recorded elevation (1e-9 rad; 1e-6 for SciPy) and still hit."""
    if _kind(loaded_engine_instance) != kind:
        pytest.skip("recorded for another engine")
    distance_m, winds, cant_deg = LEGIT_CASES[name]
    shot = _make_shot(winds, cant_deg)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance_m), lofted=True)
    angle_tolerance = SCIPY_ANGLE_TOLERANCE_RAD if kind == "scipy" else ANGLE_TOLERANCE_RAD
    assert angle >> Angular.Radian == pytest.approx(LEGIT_ANGLES[kind][name], abs=angle_tolerance)
    # A lofted flight of a minute: lift the limits that end a shot short (as the zero search does).
    fire_calc = Calculator(
        config=BaseEngineConfigDict(cMinimumVelocity=0.0, cMaximumDrop=-60000.0, cMinimumAltitude=-60000.0),
        engine=loaded_engine_instance,
    )
    if kind == "scipy" and name == "tail500":
        # This zero sits next to a jump of the error function: SciPy's adaptive trajectory there differs by metres between
        # two integrations of the same shot, so a fired shot is no check of the elevation.
        return
    # SciPy's adaptive integrator is good to a few millimetres over a minute of flight.
    tolerance_m = 5e-2 if kind == "scipy" else HEIGHT_TOLERANCE_M
    miss_m = _height_miss_m(fire_calc, shot, angle, distance_m * math.cos(shot.look_angle >> Angular.Radian))
    assert miss_m == pytest.approx(0.0, abs=tolerance_m)
