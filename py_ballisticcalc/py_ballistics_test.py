"""
TODO: Unittests
"""

import math
import unittest

from py_ballisticcalc.projectile import *
from py_ballisticcalc.drag import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.trajectory_calculator import *
from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.trajectory_data import *
from py_ballisticcalc.shot_parameters import *
from py_ballisticcalc.bmath import unit


class TestPyBallisticCalc(unittest.TestCase):

    def test_zero1(self):
        bc = BallisticCoefficient(0.365, DragTableG1)
        projectile = Projectile(bc, unit.Weight(69, unit.WeightGrain).must_create())
        ammo = Ammunition(projectile, unit.Velocity(2600, unit.VelocityFPS).must_create())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).must_create())
        weapon = Weapon(unit.Distance(3.2, unit.DistanceInch).must_create(), zero)
        atmosphere = Atmosphere()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertGreater(math.fabs(sight_angle.get_in(unit.AngularRadian) - 0.001651), 1e-6,
                           f'TestZero1 failed {sight_angle.get_in(unit.AngularRadian):.10f}')

    def test_zero2(self):
        bc = BallisticCoefficient(0.223, DragTableG7)
        projectile = Projectile(bc, unit.Weight(168, unit.WeightGrain).must_create())
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS).must_create())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).must_create())
        weapon = Weapon(unit.Distance(2, unit.DistanceInch).must_create(), zero)
        atmosphere = Atmosphere()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertGreater(math.fabs(sight_angle.get_in(unit.AngularRadian) - 0.001228), 1e-6,
                           f'TestZero2 failed {sight_angle.get_in(unit.AngularRadian):.10f}')



if __name__ == '__main__':
    unittest.main()

