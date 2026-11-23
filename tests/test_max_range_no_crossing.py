"""Maximum range when no launch angle of the bracket crosses the line of sight.

The max-range search measures each probe by the slant distance at which it comes back down through the line of sight.
A probe with no such crossing (the bracket tops out below the look angle, a degenerate bracket, a shot that starts below
``cMinimumAltitude``) counts as 0 ft, as in the C++ core, so ``find_max_range`` returns 0 ft (never an internal
sentinel) and a later zero search raises ``OutOfRangeError`` that reports a maximum range of 0 ft.
"""

import warnings

import pytest

from py_ballisticcalc import BaseEngineConfigDict, Calculator, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import *

pytestmark = pytest.mark.engine


def _make_shot(look_angle_deg: float = 0.0) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.1), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(800.0)),
        look_angle=Angular.Degree(look_angle_deg),
    )


def _max_range_ft(calc: Calculator, shot: Shot, bracket) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # one "No ZERO_DOWN found" warning per probe
        max_range, _ = calc.find_max_range(shot, bracket)
    return max_range >> Distance.Foot


@pytest.mark.parametrize("bracket", [(0.0, 10.0), (30.0, 30.0)], ids=["bracket_below_look", "degenerate_bracket"])
def test_max_range_no_crossing_is_zero(loaded_engine_instance, bracket):
    """Look 30 degrees, no elevation of the bracket rises above the line of sight: 0 ft, not a sentinel."""
    calc = Calculator(engine=loaded_engine_instance)
    assert _max_range_ft(calc, _make_shot(30.0), bracket) == 0.0


def test_max_range_start_below_minimum_altitude(loaded_engine_instance):
    """A shot that starts below cMinimumAltitude is cut at once: max range 0 ft; a zero search reports it as 0 ft."""
    calc = Calculator(config=BaseEngineConfigDict(cMinimumAltitude=100.0), engine=loaded_engine_instance)
    shot = _make_shot()
    assert _max_range_ft(calc, shot, (0.0, 90.0)) == 0.0
    for search in (calc.find_zero_angle, calc.find_zero_point):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(SolverRuntimeError) as info:
                search(shot, Distance.Meter(300.0))
        assert "9000000000" not in str(info.value)
        # (the native tiny_bclibc engine reports a plain SolverRuntimeError that carries no value)
        if isinstance(info.value, OutOfRangeError):
            assert info.value.max_range >> Distance.Foot == 0.0


_PARITY_ENGINES = (("rk4_engine", "cythonized_rk4_engine"), ("euler_engine", "cythonized_euler_engine"))


def _load(name):
    try:
        return _EngineLoader.load(name)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"engine {name} unavailable: {e}")


def _outcome(engine_name, shot, config, bracket):
    """find_max_range in feet, and max_range ft of the OutOfRangeError of a zero search (None if none).
    (The message text differs between the engines: units and a trailing "Out of range".)"""
    calc = Calculator(config=config, engine=_load(engine_name))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        max_range_ft = calc.find_max_range(shot, bracket)[0] >> Distance.Foot
        try:
            calc.find_zero_angle(shot, Distance.Meter(300.0))
            zero = None
        except OutOfRangeError as e:
            zero = e.max_range >> Distance.Foot
            assert "9000000000" not in str(e)
    return max_range_ft, zero


@pytest.mark.parametrize("python_name,cython_name", _PARITY_ENGINES)
@pytest.mark.parametrize("case", ["F_mr_br(0, 10)_look30.0", "F_start_below_minalt"])
def test_python_and_cython_agree_on_no_crossing(python_name, cython_name, case):
    """The differential-run cases: the Python engine reports the same max range and zero-search error as Cython."""
    if case == "F_mr_br(0, 10)_look30.0":
        shot, config, bracket = _make_shot(30.0), None, (0.0, 10.0)
    else:
        shot, config, bracket = _make_shot(), BaseEngineConfigDict(cMinimumAltitude=100.0), (0.0, 90.0)
    py_range, py_zero = _outcome(python_name, shot, config, bracket)
    cy_range, cy_zero = _outcome(cython_name, shot, config, bracket)
    assert py_range == cy_range == 0.0
    assert py_zero == cy_zero
    if case == "F_start_below_minalt":
        assert py_zero == 0.0
