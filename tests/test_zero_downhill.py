"""Zero angle (Ridder path) and maximum range of a shot with a DOWNHILL look angle.

``find_max_range`` runs a golden-section search over the barrel elevation, measuring each shot by the slant distance at
which it comes back down through the line of sight.  It ran with ``cMaximumDrop = 0`` ("stop at muzzle level") and the
caller's ``cMinimumAltitude``.  That is right for a level or uphill line of sight, which a shot crosses above the muzzle,
but a downhill line of sight lies *below* the muzzle: every shot was stopped before it crossed, the search converged on
about 90 degrees with a "maximum range" of a few feet and the Ridder zero search (``find_zero_angle``,
``find_zero_point``, the fallback of ``zero_angle``) raised ``OutOfRangeError`` for a target a few metres away.

A zero is correct when the shot fired with it crosses the line of sight at the target; the maximum range is correct when
no probe shot crosses the line of sight farther out.  The last test is a regression guard: results that did not depend on
the defect are unchanged (values recorded before the fix, per engine).
"""

import math
import signal
import time

import pytest

from py_ballisticcalc import BaseEngineConfigDict, Calculator, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine

LOOK_ANGLES_DEG = (-5.0, -10.0, -20.0, -30.0, -45.0)
TARGETS_M = (0.5, 0.9, 2.0, 5.0, 10.0, 50.0, 300.0)
SIGHT_HEIGHTS_M = (0.1, 0.5)
VELOCITIES_MPS = (300.0, 800.0)

# Height above the line of sight at the target (m).
HEIGHT_TOLERANCE_M = 2e-3


def _is_pure_python(engine) -> bool:
    module = getattr(engine, "__module__", "") or ""
    return module.startswith("py_ballisticcalc.engines.") and "scipy" not in module


def _skip_slow(engine, look_angle: float, distance_m: float, sight_height_m: float, velocity: float) -> None:
    """Every Ridder zero follows a max-range search of ~40 trajectories of several km: tens of seconds on the
    pure-Python engines.  They run a slice (reported repros); the fast engines run the whole grid."""
    if _is_pure_python(engine):
        if (look_angle, distance_m, sight_height_m, velocity) not in {(-20.0, 2.0, 0.1, 800.0), (-10.0, 5.0, 0.1, 800.0)}:
            pytest.skip("slow on pure-Python engines; covered by the fast engines")


def _make_shot(sight_height_m: float, mv_mps: float, look_angle_deg: float, drag_table=TableG7) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(sight_height_m), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, drag_table), Velocity.MPS(mv_mps)),
        look_angle=Angular.Degree(look_angle_deg),
    )


def _miss_m(calc: Calculator, shot: Shot, zero_angle: Angular, distance_m: float) -> float:
    """Height of the shot fired at ``zero_angle`` (barrel elevation from horizontal) above the line of sight at the
    slant distance ``distance_m``."""
    shot.relative_angle = zero_angle - shot.look_angle
    horizontal_m = distance_m * math.cos(shot.look_angle >> Angular.Radian)
    result = calc.fire(shot, Distance.Meter(horizontal_m), flags=TrajFlag.RANGE, raise_range_error=False)
    point = result[-1]
    assert point.slant_distance >> Distance.Meter == pytest.approx(distance_m, abs=1e-3)
    return point.slant_height >> Distance.Meter


@pytest.mark.parametrize("velocity", VELOCITIES_MPS)
@pytest.mark.parametrize("sight_height", SIGHT_HEIGHTS_M)
@pytest.mark.parametrize("distance", TARGETS_M)
@pytest.mark.parametrize("look_angle", LOOK_ANGLES_DEG)
def test_downhill_ridder_zero_hits_line_of_sight(loaded_engine_instance, look_angle, distance, sight_height, velocity):
    """find_zero_angle (the Ridder search) of a downhill shot finds a zero that hits."""
    _skip_slow(loaded_engine_instance, look_angle, distance, sight_height, velocity)
    shot = _make_shot(sight_height, velocity, look_angle)
    calc = Calculator(engine=loaded_engine_instance)
    angle = calc.find_zero_angle(shot, Distance.Meter(distance))
    assert _miss_m(calc, shot, angle, distance) == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)


@pytest.mark.parametrize("look_angle", (-10.0, -30.0))
@pytest.mark.parametrize("distance", (2.0, 50.0))
def test_downhill_zero_point_and_newton_path(loaded_engine_instance, look_angle, distance):
    """find_zero_point (Ridder) and zero_angle (Newton first) of a downhill shot agree and hit."""
    sight_height, velocity = 0.1, 800.0
    if _is_pure_python(loaded_engine_instance):
        pytest.skip("slow on pure-Python engines; covered by the fast engines")
    shot = _make_shot(sight_height, velocity, look_angle, TableG1)
    calc = Calculator(engine=loaded_engine_instance)
    engine = calc._engine_instance
    newton = calc.zero_angle(shot, Distance.Meter(distance))
    assert _miss_m(calc, shot, newton, distance) == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)
    if hasattr(engine, "find_zero_point"):
        point_angle, point = engine.find_zero_point(shot, Distance.Meter(distance))
        assert point.slant_height >> Distance.Meter == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)
        assert point_angle >> Angular.Degree == pytest.approx(newton >> Angular.Degree, abs=0.01)


@pytest.mark.parametrize("look_angle", (-5.0, -20.0, -45.0))
def test_downhill_max_range_is_the_maximum(loaded_engine_instance, look_angle):
    """The maximum range of a downhill shot is not a few feet: no probe shot crosses the line of sight farther out."""
    if _is_pure_python(loaded_engine_instance) and look_angle != -20.0:
        pytest.skip("slow on pure-Python engines; covered by the fast engines")
    shot = _make_shot(0.1, 800.0, look_angle)
    # Probes run with the early-termination limits lifted far enough that nothing cuts them short before they cross the
    # line of sight (40000 ft below the muzzle: the crossing of a 25 degree shot is at most 18000 ft down; a probe is not
    # stopped at the crossing by every engine, so the limit is no larger than that).
    probe_calc = Calculator(
        config=BaseEngineConfigDict(cMaximumDrop=-40000.0, cMinimumAltitude=-40000.0), engine=loaded_engine_instance
    )
    calc = Calculator(engine=loaded_engine_instance)
    max_range, angle_at_max = calc.find_max_range(shot)

    probe_max_m = 0.0
    for elevation_deg in (25.0,) if _is_pure_python(loaded_engine_instance) else (20.0, 25.0, 30.0):
        shot.relative_angle = Angular.Degree(elevation_deg) - shot.look_angle
        result = probe_calc.fire(shot, Distance.Meter(40000), flags=TrajFlag.ZERO_DOWN, raise_range_error=False)
        crossings = [p for p in result if p.flag & TrajFlag.ZERO_DOWN]
        assert crossings, f"probe at {elevation_deg} deg did not come back down through the line of sight"
        probe_max_m = max(probe_max_m, crossings[0].slant_distance >> Distance.Meter)

    got_m = max_range >> Distance.Meter
    assert got_m >= probe_max_m * (1 - 1e-3)
    assert got_m <= probe_max_m * 1.05
    assert 1.0 < angle_at_max >> Angular.Degree < 89.0


def test_downhill_out_of_range_is_still_reported(loaded_engine_instance):
    """A target beyond the (now real) maximum range raises OutOfRangeError that reports it."""
    if _is_pure_python(loaded_engine_instance):
        pytest.skip("slow on pure-Python engines; covered by the fast engines")
    shot = _make_shot(0.1, 300.0, -20.0)
    calc = Calculator(engine=loaded_engine_instance)
    max_range, _ = calc.find_max_range(shot)
    assert max_range >> Distance.Meter > 1000.0
    # (the native tiny_bclibc engine reports it as a plain SolverRuntimeError, the base class of OutOfRangeError)
    with pytest.raises(SolverRuntimeError) as info:
        calc.find_zero_angle(shot, Distance.Meter(2.0 * (max_range >> Distance.Meter)))
    if isinstance(info.value, OutOfRangeError):
        assert info.value.max_range >> Distance.Meter == pytest.approx(max_range >> Distance.Meter, rel=1e-6)
    else:
        assert "out of range" in str(info.value)



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


def test_downhill_max_range_tiny_bracket_ends(loaded_engine_instance):
    """A shot launched a hair above a slightly downhill line of sight cannot rise by its sight height: no crossing, so
    nothing to integrate for ever with the limits lifted (it used to run until the range limit)."""
    shot = _make_shot(0.1, 800.0, -0.001)
    calc = Calculator(engine=loaded_engine_instance)
    start = time.monotonic()
    max_range, _ = _run_with_time_bound(60, calc.find_max_range, shot, (0.0, 0.0001))
    assert time.monotonic() - start < 30
    assert max_range >> Distance.Foot == 0.0


def test_downhill_max_range_wide_bracket_ends(loaded_engine_instance):
    """A bracket that includes elevations at or below the look angle (-90..90) does not integrate those shots (they
    cannot rise above the line of sight) and finds the same maximum as the bracket (0, 90)."""
    if _is_pure_python(loaded_engine_instance):
        pytest.skip("slow on pure-Python engines (the search alone takes minutes); covered by the fast engines")
    shot = _make_shot(0.1, 800.0, -20.0)
    calc = Calculator(engine=loaded_engine_instance)
    wide, _ = _run_with_time_bound(60, calc.find_max_range, shot, (-90.0, 90.0))
    narrow, _ = calc.find_max_range(shot, (0.0, 90.0))
    assert wide >> Distance.Foot == pytest.approx(narrow >> Distance.Foot, rel=1e-3)


@pytest.mark.parametrize("entry", ("zero_angle", "find_zero_angle"))
def test_long_downhill_zero_with_default_limits(loaded_engine_instance, entry):
    """A long downhill zero (1500 m at -30 degrees: the target is 750 m below the muzzle) needs the drop and altitude
    limits widened to the required drop; with the default limits the Python Newton search used to stop short and answer
    -23.5 deg instead of -28.3 deg (the altitude test compared the wrong way round)."""
    if _is_pure_python(loaded_engine_instance):
        pytest.skip("slow on pure-Python engines; covered by the fast engines")
    shot = _make_shot(0.1, 800.0, -30.0)
    calc = Calculator(engine=loaded_engine_instance)
    angle = getattr(calc, entry)(shot, Distance.Meter(1500.0))
    # (fired with the limits lifted: at the default altitude limit of -1500 ft the shot itself stops short of 1500 m)
    fire_calc = Calculator(
        config=BaseEngineConfigDict(cMaximumDrop=-40000.0, cMinimumAltitude=-40000.0), engine=loaded_engine_instance
    )
    assert _miss_m(fire_calc, shot, angle, 1500.0) == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)


def test_first_zero_down_standalone():
    """`_first_zero_down` works when called directly (not only from `_find_max_range`), downhill or not."""
    import math

    from py_ballisticcalc.engines import RK4IntegrationEngine

    shot = _make_shot(0.1, 800.0, -20.0)
    engine = RK4IntegrationEngine({})
    props = engine._init_trajectory(shot)
    # a shot launched below the line of sight has nothing to cross (answered without integrating)
    props.barrel_elevation_rad = math.radians(-30.0)
    assert engine._first_zero_down(props) is None
    props.barrel_elevation_rad = math.radians(-10.0)
    cross = engine._first_zero_down(props)
    assert cross is not None
    assert cross.slant_height >> Distance.Meter == pytest.approx(0.0, abs=1e-2)

# ---------------------------------------------------------------------------------------------------------------
# Regression guard: results that did not depend on the defect.  Recorded before the fix, per engine class module.
# (kind, look_angle_deg, distance_m) -> value;  kinds: "max_range_m", "max_angle_deg", "ridder_deg", "newton_deg"
# ---------------------------------------------------------------------------------------------------------------

from tests.zero_downhill_guard import GUARD  # noqa: E402


def _guard_value(calc: Calculator, kind: str, look_angle: float, distance: float) -> float:
    shot = _make_shot(0.1, 800.0, look_angle)
    if kind == "ridder_deg":
        return calc.find_zero_angle(shot, Distance.Meter(distance)) >> Angular.Degree
    return calc.zero_angle(shot, Distance.Meter(distance)) >> Angular.Degree


def test_unchanged_results(loaded_engine_instance):
    """Maximum range of level and uphill shots, their Ridder zeros, and the Newton zeros of downhill shots are what
    they were before the fix."""
    key = f"{loaded_engine_instance.__module__}.{loaded_engine_instance.__name__}"
    recorded = GUARD.get(key)
    if recorded is None:
        pytest.skip(f"no values recorded for {key}")
    calc = Calculator(engine=loaded_engine_instance)
    max_ranges: dict[float, tuple] = {}  # one search per look angle serves both the range and its angle
    for (kind, look_angle, distance), value in recorded.items():
        if kind in ("max_range_m", "max_angle_deg"):
            if look_angle not in max_ranges:
                max_ranges[look_angle] = calc.find_max_range(_make_shot(0.1, 800.0, look_angle))
            got = max_ranges[look_angle][0] >> Distance.Meter if kind == "max_range_m" else max_ranges[look_angle][1] >> Angular.Degree
        else:
            got = _guard_value(calc, kind, look_angle, distance)
        # SciPy's bounded Brent search minimises a noisy objective (about 1e-3 ft near the optimum): the last-bit differences of
        # another CPU or libm move its maximum-range result by ~1e-8 relative (observed 4e-8 in CI), so those entries are
        # compared to 1e-6; everything else stays at 1e-9.
        scipy_search = kind in ("max_range_m", "max_angle_deg") and "scipy" in loaded_engine_instance.__module__
        rel = 1e-6 if scipy_search else 1e-9
        assert got == pytest.approx(value, rel=rel, abs=1e-9), (kind, look_angle, distance)
