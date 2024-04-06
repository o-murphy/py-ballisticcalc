"""Unittests for the py_ballisticcalc library"""

import unittest
import copy
from py_ballisticcalc import (
    DragModel, Ammo, Weapon, Calculator, Shot, Wind, Atmo, TableG7,
    get_global_use_powder_sensitivity, set_global_use_powder_sensitivity
)
from py_ballisticcalc.unit import *


class TestComputer(unittest.TestCase):
    """Basic verifications that wind, spin, and cant values produce effects of correct sign and magnitude"""

    def setUp(self):
        """Baseline shot has barrel at zero elevation"""
        self.range = 1000
        self.step = 100
        self.dm = DragModel(0.22, TableG7, 168, 0.308, 1.22)
        self.ammo = Ammo(self.dm, Velocity.FPS(2600))
        self.weapon = Weapon(4, 12)
        self.atmosphere = Atmo.icao()  # Standard sea-level atmosphere
        self.calc = Calculator()
        self.baseline_shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere)
        self.baseline_trajectory = self.calc.fire(shot=self.baseline_shot, trajectory_range=self.range, trajectory_step=self.step)

#region Cant_angle
    def test_cant_zero_elevation(self):
        """Cant_angle = 90 degrees with zero barrel elevation should match baseline with:
            drop+=sight_height, windage-=sight_height
        """
        canted = copy.copy(self.baseline_shot)
        canted.cant_angle = Angular.Degree(90)
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        self.assertAlmostEqual(t.trajectory[5].height.raw_value-self.weapon.sight_height.raw_value,
                                self.baseline_trajectory[5].height.raw_value)
        self.assertAlmostEqual(t.trajectory[5].windage.raw_value+self.weapon.sight_height.raw_value,
                                self.baseline_trajectory[5].windage.raw_value)

    def test_cant_positive_elevation(self):
        """Cant_angle = 90 degrees with positive barrel elevation and zero twist should match baseline with:
            drop+=sight_height, windage-=sight_height at muzzle, increasingly positive down-range
        """
        canted = Shot(weapon=Weapon(sight_height=self.weapon.sight_height, twist=0, zero_elevation=Angular.Mil(2)),
                    ammo=self.ammo, atmo=self.atmosphere, cant_angle=Angular.Degree(90))
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        self.assertAlmostEqual(t.trajectory[5].height.raw_value-self.weapon.sight_height.raw_value,
                                self.baseline_trajectory[5].height.raw_value, 2)
        self.assertAlmostEqual(t.trajectory[0].windage.raw_value, -self.weapon.sight_height.raw_value)
        self.assertGreater(t.trajectory[5].windage.raw_value, t.trajectory[3].windage.raw_value)

    def test_cant_zero_sight_height(self):
        """Cant_angle = 90 degrees with sight_height=0 and barrel_elevation=0 should match baseline with:
            drop+=baseline.sight_height, windage no change
        """
        canted = Shot(weapon=Weapon(sight_height=0, twist=self.weapon.twist),
                    ammo=self.ammo, atmo=self.atmosphere, cant_angle=Angular.Degree(90))
        t = self.calc.fire(canted, trajectory_range=self.range, trajectory_step=self.step)
        self.assertAlmostEqual(t.trajectory[5].height.raw_value-self.weapon.sight_height.raw_value,
                                self.baseline_trajectory[5].height.raw_value)
        self.assertAlmostEqual(t.trajectory[5].windage, self.baseline_trajectory[5].windage)
#endregion Cant_angle

#region Wind
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
        self.assertGreater(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_wind_from_front(self):
        """Wind from in front should increase drop"""
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=self.atmosphere,
                    winds=[Wind(Velocity(5, Velocity.MPH), Angular(6, Angular.OClock))])
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(t.trajectory[5].height, self.baseline_trajectory[5].height)
#endregion Wind
        
#region Twist
    def test_no_twist(self):
        """Barrel with no twist should have no spin drift"""
        shot = Shot(weapon=Weapon(twist=0), ammo=self.ammo, atmo=self.atmosphere)
        t = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertEqual(t.trajectory[5].windage.raw_value, 0)

    def test_twist(self):
        """Barrel with right-hand twist should have positive spin drift.
            Barrel with left-hand twist should have negative spin drift.
            Faster twist rates should produce larger drift.
        """
        shot = Shot(weapon=Weapon(twist=12), ammo=self.ammo, atmo=self.atmosphere)
        twist_right = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(twist_right.trajectory[5].windage.raw_value, 0)
        shot = Shot(weapon=Weapon(twist=-8), ammo=self.ammo, atmo=self.atmosphere)
        twist_left = self.calc.fire(shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(twist_left.trajectory[5].windage.raw_value, 0)
        # Faster twist should produce larger drift:
        self.assertGreater(-twist_left.trajectory[5].windage.raw_value, twist_right.trajectory[5].windage.raw_value)
#endregion Twist

#region Atmo
    def test_humidity(self):
        """Increasing relative humidity should decrease drop (due to decreasing density)"""
        humid = Atmo(humidity=.9)  # 90% humidity
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=humid)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_temp_atmo(self):
        """Dropping temperature should increase drop (due to increasing density)"""
        cold = Atmo(temperature=Temperature.Celsius(0))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_altitude(self):
        """Increasing altitude should decrease drop (due to decreasing density)"""
        high = Atmo.icao(Distance.Foot(5000))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=high)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_pressure(self):
        """Decreasing pressure should decrease drop (due to decreasing density)"""
        thin = Atmo(pressure=Pressure.InHg(20.0))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=thin)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].height, self.baseline_trajectory[5].height)
#endregion Atmo

#region Ammo
    def test_ammo_drag(self):
        """Increasing ballistic coefficient (bc) should decrease drop"""
        tdm = DragModel(self.dm.BC+0.5, self.dm.drag_table, self.dm.weight, self.dm.diameter, self.dm.length)
        slick = Ammo(tdm, self.ammo.mv)
        shot = Shot(weapon=self.weapon, ammo=slick, atmo=self.atmosphere)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertGreater(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_ammo_optional(self):
        """DragModel.weight and .diameter, and Ammo.length, are only relevant when computing
            spin-drift.  Drop should match baseline with those parameters omitted.
        """
        tdm = DragModel(self.dm.BC, self.dm.drag_table)
        tammo = Ammo(tdm, mv=self.ammo.mv)
        shot = Shot(weapon=self.weapon, ammo=tammo, atmo=self.atmosphere)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertEqual(t.trajectory[5].height, self.baseline_trajectory[5].height)

    def test_powder_sensitivity(self):
        """With _globalUsePowderSensitivity: Reducing temperature should reduce muzzle velocity"""
        previous = get_global_use_powder_sensitivity()
        set_global_use_powder_sensitivity(True)
        self.ammo.calc_powder_sens(Velocity.FPS(2550), Temperature.Celsius(0))
        cold = Atmo(temperature=Temperature.Celsius(-5))
        shot = Shot(weapon=self.weapon, ammo=self.ammo, atmo=cold)
        t = self.calc.fire(shot=shot, trajectory_range=self.range, trajectory_step=self.step)
        self.assertLess(t.trajectory[0].velocity, self.baseline_trajectory[0].velocity)
        set_global_use_powder_sensitivity(previous)

#endregion Ammo

if __name__ == '__main__':
    unittest.main()
