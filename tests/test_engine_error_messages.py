"""The exceptions of the cythonized engines carry the same type and text as the pure-Python engines.

The C++ core decorates some messages with a kind prefix ("Value error (...).", "Runtime error (...)"); the Cython
wrapper strips it, so a caller that matches on the text sees the same thing on every engine.

Intentionally NOT aligned (documented): the text and unit of ``OutOfRangeError`` (Python keeps the caller's unit, the
C++ core reports feet and appends ". Out of range").
"""

import pytest

from py_ballisticcalc import Ammo, Calculator, DragModel, Shot, SolverRuntimeError, TableG7, Weapon
from py_ballisticcalc.unit import Angular, Distance, Velocity

pytestmark = pytest.mark.engine


def _skip_tiny(engine) -> None:
    if engine.__module__.startswith("tiny_bclibc"):
        pytest.skip("tiny_bclibc uses its own error codes")


def _shot(elevation_deg: float, muzzle_mps: float = 800.0) -> Shot:
    return Shot(
        weapon=Weapon(sight_height=Distance.Meter(0.1), twist=Distance.Inch(11)),
        ammo=Ammo(DragModel(0.243, TableG7), Velocity.MPS(muzzle_mps)),
        relative_angle=Angular.Degree(elevation_deg),
    )


@pytest.mark.parametrize("elevation_deg", [0.0, -1.0], ids=["zero", "negative"])
def test_find_apex_needs_positive_elevation(loaded_engine_instance, elevation_deg):
    """find_apex with barrel elevation <= 0: ValueError, text without the C++ "Value error (...)" decoration."""
    _skip_tiny(loaded_engine_instance)
    calc = Calculator(engine=loaded_engine_instance)
    with pytest.raises(ValueError) as info:
        calc.find_apex(_shot(elevation_deg))
    assert str(info.value) == "Barrel elevation must be greater than 0 to find apex."


def test_find_apex_no_apex_text_is_undecorated(loaded_engine_instance):
    """A shot that has no apex to flag: no "Runtime error (...)" decoration in the SolverRuntimeError text.

    The Python engines flag an apex (or return one at the muzzle) for this shot; the C++ core may report that none
    was flagged. Whichever it is, the text must be the Python one.
    """
    _skip_tiny(loaded_engine_instance)
    calc = Calculator(engine=loaded_engine_instance)
    try:
        calc.find_apex(_shot(1.0, muzzle_mps=0.5))
    except SolverRuntimeError as e:
        assert type(e) is SolverRuntimeError
        assert str(e) == "No apex flagged in trajectory data"
