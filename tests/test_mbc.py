"Unit tests of multiple-BC drag models"

import unittest
from py_ballisticcalc import *


class TestMBC(unittest.TestCase):

    def setUp(self) -> None:
        "Establish baseline trajectory"
        self.range = 1000
        self.step = 100
        self.dm = DragModel(0.22, TableG7)
        self.ammo = Ammo(self.dm, Velocity.FPS(2600))
        self.weapon = Weapon(4, 12)
        self.calc = Calculator()
        self.baseline_shot = Shot(weapon=self.weapon, ammo=self.ammo)
        self.baseline_trajectory = self.calc.fire(shot=self.baseline_shot, trajectory_range=self.range, trajectory_step=self.step).trajectory

    def test_mbc1(self):
        "We should get the same trajectory whether we give single BC or use multi-BC with single value"
        dm_multi = DragModel([BCpoint(.22, V=Velocity.FPS(2500)), BCpoint(.22, V=Velocity.FPS(1500)), BCpoint(BC=.22, Mach=3)], TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range, trajectory_step=self.step).trajectory
        for i in range(len(multi_trajectory)):
            self.assertEqual(multi_trajectory[i].formatted(), self.baseline_trajectory[i].formatted())

    def test_mbc2(self):
        "Setting different BC above muzzle velocity should have no effect"
        dm_multi = DragModel([BCpoint(.22, V=Velocity.FPS(2700)), BCpoint(.5, V=Velocity.FPS(3500))], TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range, trajectory_step=self.step).trajectory
        for i in range(len(multi_trajectory)):
            self.assertEqual(multi_trajectory[i].formatted(), self.baseline_trajectory[i].formatted())

    def test_mbc3(self):
        "Setting higher BC should result in higher downrange velocities"
        # So here we'll boost the BC for velocities lower than the baseline's velocity at 200 yards
        dm_multi = DragModel([BCpoint(.5, V=self.baseline_trajectory[3].velocity), BCpoint(.22, V=self.baseline_trajectory[2].velocity)], TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range, trajectory_step=self.step).trajectory
        # Should show no change before 200 yards
        self.assertEqual(multi_trajectory[1].velocity.raw_value, self.baseline_trajectory[1].velocity.raw_value)
        # Should be faster at any point after 200 yards
        self.assertGreater(multi_trajectory[4].velocity.raw_value, self.baseline_trajectory[4].velocity.raw_value)
