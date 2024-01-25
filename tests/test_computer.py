"""Unittests for the py_ballisticcalc library"""

import unittest
from math import fabs
from py_ballisticcalc import *


class TestComputer(unittest.TestCase):

    def setUp(self):
        self.range = 1000
        self.step = 100
        self.dm = DragModel(0.22, TableG7, 168, 0.308)
        self.ammo = Ammo(self.dm, 1.22, Velocity(2600, Velocity.FPS))
        self.weapon = Weapon(4, 12)
        self.atmosphere = Atmo.icao()
        self.calc = Calculator()
        self.baseline_shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere)
        self.baseline_trajectory = self.calc.fire(shot=self.baseline_shot, trajectory_range=self.range, trajectory_step=self.step)

    def test_wind_from_left(self):
        """Wind from left should increase windage"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(3, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].windage, self.baseline_trajectory[5].windage)

    def test_wind_from_right(self):
        """Wind from right should decrease windage"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(9, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(t.trajectory[5].windage, self.baseline_trajectory[5].windage)

    def test_wind_from_back(self):
        """Wind from behind should decrease drop"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(0, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].drop, self.baseline_trajectory[5].drop)

    def test_wind_from_front(self):
        """Wind from in front should increase drop"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(6, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(t.trajectory[5].drop, self.baseline_trajectory[5].drop)

    def test_no_twist(self):
        """Barrel with no twist should have no spin drift"""
        shot = Shot(weapon=Weapon(twist=0), ammo=self.ammo, atmo=self.atmosphere)
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertEqual(t.trajectory[5].windage.raw_value, 0)

    def test_twist_right(self):
        """Barrel with right-hand twist should have positive spin drift"""
        shot = Shot(weapon=Weapon(twist=10), ammo=self.ammo, atmo=self.atmosphere)
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].windage.raw_value, 0)


if __name__ == '__main__':
    unittest.main()
