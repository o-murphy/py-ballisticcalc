"""Parity of the prototype with the Cython-over-C++ engines of py_ballisticcalc_exts: the six engines (the whole trajectory,
bit for bit), zero_point and the dense sequence.

    PYTHONPATH=build python check.py        # py_ballisticcalc and py_ballisticcalc_exts must be importable too
"""

import logging

from py_ballisticcalc import Ammo, Calculator, Distance, DragModel, Shot, TableG7, TrajFlag, Velocity, Weapon, Weight
from py_ballisticcalc.logger import logger

logger.setLevel(logging.ERROR)
NAMES = ("Euler", "RK4", "VelocityVerlet", "CashKarp", "DormandPrince", "Tsitouras")


def shot(zero):
    dm = DragModel(0.22, TableG7, weight=Weight.Gram(10), diameter=Distance.Centimeter(7.62), length=Distance.Centimeter(3.0))
    return Shot(weapon=Weapon(sight_height=Distance.Centimeter(4), twist=Distance.Centimeter(30)), ammo=Ammo(dm=dm, mv=Velocity.MPS(800)))


def engine(spec):
    calc = Calculator(engine=spec)
    return calc._engine_factory(calc.config)


def key(d):
    return (d.time, d.position.x, d.position.y, d.position.z, d.velocity.x, d.velocity.y, d.velocity.z, d.mach)


worst = 0.0
for n in NAMES:
    cpp, cabi = (engine(f"py_ballisticcalc_exts:Cythonized{n}IntegrationEngine"), engine(f"bcy:Native{n}IntegrationEngine"))
    a = cpp.integrate(shot(False), Distance.Meter(2000), Distance.Meter(100), 0.0, TrajFlag.ALL, True)
    b = cabi.integrate(shot(False), Distance.Meter(2000), Distance.Meter(100), 0.0, TrajFlag.ALL, True)
    assert len(a.records) == len(b.records), n
    diff = max(
        max(abs(x.time - y.time), abs(x.distance.raw_value - y.distance.raw_value), abs(x.height.raw_value - y.height.raw_value),
            abs(x.velocity.raw_value - y.velocity.raw_value), abs(x.energy.raw_value - y.energy.raw_value)) + (x.flag != y.flag)
        for x, y in zip(a.records, b.records)
    )
    dense = len(a.base_data) == len(b.base_data) and all(key(x) == key(y) for x, y in zip(a.base_data, b.base_data))
    angle_a, point_a = cpp.zero_point(shot(True), Distance.Meter(100))
    angle_b, point_b = cabi.zero_point(shot(True), Distance.Meter(100))
    same_zero = (angle_a.raw_value, point_a.time) == (angle_b.raw_value, point_b.time)
    print(f"{n:15} {len(a.records):3} records, max abs diff {diff}, dense {len(a.base_data)}/{len(b.base_data)} equal={dense}, zero_point equal={same_zero}")
    worst = max(worst, diff)
    assert diff == 0 and dense and same_zero, n
print("bit-exact" if worst == 0 else f"worst {worst}")
