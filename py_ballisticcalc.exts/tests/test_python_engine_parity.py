"""Records of the pure-Python engines against the Cython (bclibc C ABI) engines, field by field.

Replaces the removed harness-level parity test (drag, density ratio, mach, spin drift, energy, stability of the old
C++ ShotProps): the same quantities are in every ``TrajectoryData`` record, so comparing records covers them.

``python+rk4`` vs ``cython+rk4`` and ``python+euler`` vs ``cython+euler`` run the same algorithm with the same step, so
the records have the same length, the same flags and the same values up to floating point differences.

Measured tolerance (3 shots: look angle 0/+2/-5 deg, twist 0/11/12 in, 7.62 mm 175 gr G7, ICAO, 1500 m at 50 m step,
all fields of ``TrajectoryData`` in raw units): the largest ``|python - cython| / (|cython| + 1e-6)`` is 5.0e-8 for
rk4 and 5.4e-8 for euler, both in ``angle`` (the next ones: drag 1.8e-8, height 1.0e-8, ogw 3.2e-9). The assertions
use rel=1e-6, abs=1e-6, i.e. 20x above the measured maximum.
"""

import pytest

from py_ballisticcalc import (
    Ammo,
    Angular,
    Atmo,
    Calculator,
    Distance,
    DragModel,
    Shot,
    TableG7,
    Velocity,
    Weapon,
    Weight,
)
from py_ballisticcalc.trajectory_data import TrajFlag

REL = 1e-6
ABS = 1e-6

SHOTS = [(0.0, 0.0), (2.0, 11.0), (-5.0, 12.0)]  # (look angle deg, twist in)


def _shot(look_deg: float, twist_in: float) -> Shot:
    dm = DragModel(0.243, TableG7, Weight.Grain(175), Distance.Millimeter(7.62), Distance.Millimeter(32.0))
    return Shot(
        ammo=Ammo(dm, mv=Velocity.MPS(800)),
        weapon=Weapon(sight_height=Distance.Centimeter(5), twist=Distance.Inch(twist_in)),
        atmo=Atmo.icao(),
        look_angle=Angular.Degree(look_deg),
    )


def _raw(x):
    return getattr(x, "_value", x)


@pytest.mark.parametrize("method", ["rk4", "euler"])
@pytest.mark.parametrize("look_deg,twist_in", SHOTS)
def test_records_match_python_engine(method, look_deg, twist_in):
    py = Calculator(engine=f"python+{method}")
    cy = Calculator(engine=f"cython+{method}")
    shot = _shot(look_deg, twist_in)
    args = (Distance.Meter(1500), Distance.Meter(50), TrajFlag.ALL)

    rp = py.integrate(shot, *args).records
    rc = cy.integrate(shot, *args).records

    assert len(rp) == len(rc) > 10
    for a, b in zip(rp, rc):
        for name in a._fields:
            x, y = _raw(getattr(a, name)), _raw(getattr(b, name))
            if name == "flag":
                assert x == y, (name, x, y)
            else:
                assert x == pytest.approx(y, rel=REL, abs=ABS), (name, a.time, x, y)
