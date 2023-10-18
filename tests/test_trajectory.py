"""Unittests for the py_ballisticcalc library"""

import unittest
from math import fabs
from py_ballisticcalc import *


class TestTrajectory(unittest.TestCase):

    def test_zero1(self):
        dm = DragModel(0.365, TableG1, 69, 0.223)
        ammo = Ammo(dm, 0.9, 2600)
        weapon = Weapon(Distance(3.2, Distance.Inch), Distance(100, Distance.Yard))
        atmosphere = Atmo.icao()
        calc = TrajectoryCalc(ammo)

        zero_angle = calc.zero_angle(weapon, atmosphere)

        self.assertAlmostEqual(zero_angle >> Angular.Radian, 0.001651, 6,
                               f'TestZero1 failed {zero_angle >> Angular.Radian:.10f}')

    def test_zero2(self):
        dm = DragModel(0.223, TableG7, 69, 0.223)
        ammo = Ammo(dm, 0.9, 2750)
        weapon = Weapon(Distance(2, Distance.Inch), Distance(100, Distance.Yard))
        atmosphere = Atmo.icao()
        calc = TrajectoryCalc(ammo)

        zero_angle = calc.zero_angle(weapon, atmosphere)

        self.assertAlmostEqual(zero_angle >> Angular.Radian, 0.001228, 6,
                               f'TestZero2 failed {zero_angle >> Angular.Radian:.10f}')

    def custom_assert_equal(self, a, b, accuracy, name):
        with self.subTest(name=name):
            self.assertLess(fabs(a - b), accuracy, f'Assertion {name} failed ({a}/{b}, {accuracy})')

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float,
                     mach: float, energy: float, path: float, hold: float,
                     windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: Unit):

        self.custom_assert_equal(distance, data.distance >> Distance.Yard, 0.001, "Distance")
        self.custom_assert_equal(velocity, data.velocity >> Velocity.FPS, 5, "Velocity")
        self.custom_assert_equal(mach, data.mach, 0.005, "Mach")
        self.custom_assert_equal(energy, data.energy >> Energy.FootPound, 5, "Energy")
        self.custom_assert_equal(time, data.time, 0.06, "Time")
        self.custom_assert_equal(ogv, data.ogw >> Weight.Pound, 1, "OGV")

        if distance >= 800:
            self.custom_assert_equal(path, data.drop >> Distance.Inch, 4, 'Drop')
        elif distance >= 500:
            self.custom_assert_equal(path, data.drop >> Distance.Inch, 1, 'Drop')
        else:
            self.custom_assert_equal(path, data.drop >> Distance.Inch, 0.5, 'Drop')

        if distance > 1:
            self.custom_assert_equal(hold, data.drop_adj >> adjustment_unit, 0.5, 'Hold')

        if distance >= 800:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1.5, "Windage")
        elif distance >= 500:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1, "Windage")
        else:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 0.5, "Windage")

        if distance > 1:
            self.custom_assert_equal(wind_adjustment,
                                     data.windage_adj >> adjustment_unit, 0.5, "WAdj")

    def test_path_g1(self):
        dm = DragModel(0.223, TableG1, 168, 0.308)
        ammo = Ammo(dm, 1.282, Velocity(2750, Velocity.FPS))
        weapon = Weapon(Distance(2, Distance.Inch), Distance(100, Distance.Yard))
        atmosphere = Atmo.icao()
        shot_info = Shot(1000,
                         zero_angle=Angular(0.001228, Angular.Radian),
                         atmo=atmosphere,
                         winds=[Wind(Velocity(5, Velocity.MPH), Angular(10.5, Angular.OClock))])
        calc = TrajectoryCalc(ammo)
        data = calc.trajectory(weapon, shot_info, Distance.Yard(100))

        self.custom_assert_equal(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, Angular.MOA],
            [data[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, Angular.MOA],
            [data[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, Angular.MOA],
            [data[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, Angular.MOA]
        ]

        for i, d in enumerate(test_data):
            with self.subTest(f"validate one {i}"):
                self.validate_one(*d)

    def test_path_g7(self):
        dm = DragModel(0.223, TableG7, 168, 0.308)
        ammo = Ammo(dm, 1.282, Velocity(2750, Velocity.FPS))
        weapon = Weapon(2, 100, 11.24)
        shot_info = Shot(Distance.Yard(1000),
                         zero_angle=Angular.MOA(4.221),
                         winds=[Wind(Velocity(5, Velocity.MPH), -45)])

        calc = TrajectoryCalc(ammo)
        data = calc.trajectory(weapon, shot_info, Distance.Yard(100))

        self.custom_assert_equal(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, Angular.Mil],
            [data[1], 100, 2544.3, 2.279, 2416, 0, 0, -0.35, -0.09, 0.113, 698, Angular.Mil],
            [data[5], 500, 1810.7, 1.622, 1226, -56.3, -3.18, -9.96, -0.55, 0.673, 252, Angular.Mil],
            [data[10], 1000, 1081.3, 0.968, 442, -401.6, -11.32, -50.98, -1.44, 1.748, 55, Angular.Mil]
        ]

        for i, d in enumerate(test_data):
            with self.subTest(f"validate one {i}"):
                self.validate_one(*d)


if __name__ == '__main__':
    unittest.main()
