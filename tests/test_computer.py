"""Unittests for the py_ballisticcalc library"""

import unittest
from math import fabs
from py_ballisticcalc import *


class TestComputer(unittest.TestCase):

    def setUp(self):
        self.dm = DragModel(0.22, TableG7, 168, 0.308)
        self.ammo = Ammo(self.dm, 1.22, Velocity(2600, Velocity.FPS))
        self.weapon = Weapon(4, 12)
        self.atmosphere = Atmo.icao()
        self.calc = Calculator(self.weapon, self.ammo)
        self.baseline_shot = Shot(weapon=self.weapon, atmo=self.atmosphere)
        self.baseline_trajectory = self.calc.fire(shot=self.baseline_shot, trajectory_range=1000, trajectory_step=100)

    def test_wind_from_left(self):
        shot = Shot(weapon=self.weapon, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(3, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=1000, trajectory_step=100)
        self.assertGreater(t.trajectory[5].windage, self.baseline_trajectory[5].windage)


if __name__ == '__main__':
    unittest.main()
