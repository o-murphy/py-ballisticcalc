"""Unittests for the py_ballisticcalc library"""

import unittest
from math import fabs

import pyximport

pyximport.install(language_level=3)
from py_ballisticcalc import Distance, Weight, Velocity, Angular, Calculator
from py_ballisticcalc import Temperature, Pressure, Energy, Unit
from py_ballisticcalc import DragModel, Ammo, Weapon, Wind, Shot, Atmo
from py_ballisticcalc import TableG7, TableG1, MultiBC
from py_ballisticcalc import TrajectoryData, TrajectoryCalc


class TestMBC(unittest.TestCase):

    def test_mbc(self):
        mbc = MultiBC(
            drag_table=TableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            mbc_table=[{'BC': p[0], 'V': p[1]} for p in ((0.275, 800), (0.255, 500), (0.26, 700))],
        )
        dm = DragModel.from_mbc(mbc)
        ammo = Ammo(dm, 1, 800)
        cdm = TrajectoryCalc(ammo=ammo).cdm
        self.assertIsNot(cdm, None)
        ret = list(cdm)
        self.assertEqual(ret[0], {'Mach': 0.0, 'CD': 0.1259323091692403})
        self.assertEqual(ret[-1], {'Mach': 5.0, 'CD': 0.15771258594668947})


class TestInterface(unittest.TestCase):

    def setUp(self) -> None:
        dm = DragModel(0.22, TableG7, 168, 0.308)
        self.ammo = Ammo(dm, 1.22, Velocity(2600, Velocity.FPS))
        self.atmosphere = Atmo.icao()

    @unittest.skip(reason="Fixme: zero_given_elevation")
    def test_zero_given(self):

        for sh in [0, 2, 3]:

            for reference_distance in range(100, 600, 200):
                with self.subTest(zero_range=reference_distance, sight_height=sh):
                    weapon = Weapon(Distance.Inch(sh), Distance.Yard(reference_distance), 11.24)
                    calc = Calculator(weapon, self.ammo, self.atmosphere)
                    calc.update_elevation()
                    # print('\nelevation', calc.elevation << Angular.MOA)
                    calc.weapon.sight_height = Distance.Inch(sh)
                    zero_given = calc.zero_given_elevation(calc.elevation)
                    zero_range = zero_given.distance >> Distance.Yard
                    self.assertAlmostEqual(zero_range, reference_distance, 7)

    @unittest.skip(reason="Fixme: danger_space")
    def test_danger_space(self):
        winds = [Wind()]
        weapon = Weapon(Distance.Inch(0), Distance.Yard(400), 11.24)
        calc = Calculator(weapon, self.ammo, self.atmosphere)
        calc.update_elevation()
        print('aim', calc.elevation << Angular.MOA)
        zero_given = calc.zero_given_elevation(calc.elevation, winds)
        print(zero_given.distance << Distance.Yard)
        print(calc.test_danger_space(zero_given, Distance.Meter(1.7)) << Distance.Meter)
        print(calc.danger_space(zero_given, Distance.Meter(1.5)) << Distance.Meter)
        print(calc.danger_space(zero_given, Distance.Inch(10)) << Distance.Yard)


class TestTrajectory(unittest.TestCase):

    def test_zero1(self):
        dm = DragModel(0.365, TableG1, 69, 0.223)
        ammo = Ammo(dm, 0.9, 2600)
        weapon = Weapon(Distance(3.2, Distance.Inch), Distance(100, Distance.Yard))
        atmosphere = Atmo.icao()
        calc = TrajectoryCalc(ammo)

        sight_angle = calc.sight_angle(weapon, atmosphere)

        self.assertAlmostEqual(sight_angle >> Angular.Radian, 0.001651, 6,
                               f'TestZero1 failed {sight_angle >> Angular.Radian:.10f}')

    def test_zero2(self):
        dm = DragModel(0.223, TableG7, 69, 0.223)
        ammo = Ammo(dm, 0.9, 2750)
        weapon = Weapon(Distance(2, Distance.Inch), Distance(100, Distance.Yard))
        atmosphere = Atmo.icao()
        calc = TrajectoryCalc(ammo)

        sight_angle = calc.sight_angle(weapon, atmosphere)

        self.assertAlmostEqual(sight_angle >> Angular.Radian, 0.001228, 6,
                               f'TestZero2 failed {sight_angle >> Angular.Radian:.10f}')

    def custom_assert_equal(self, a, b, accuracy, name):
        with self.subTest():
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
        shot_info = Shot(1000, 100, sight_angle=Angular(0.001228, Angular.Radian))
        wind = [Wind(Velocity(5, Velocity.MPH), Angular(10.5, Angular.OClock))]
        calc = TrajectoryCalc(ammo)
        data = calc.trajectory(weapon, atmosphere, shot_info, wind)

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
        atmosphere = Atmo.icao()
        shot_info = Shot(Distance.Yard(1000),
                         Distance.Yard(100),
                         sight_angle=Angular.MOA(4.221)
                         )
        wind = [Wind(Velocity(5, Velocity.MPH), -45)]

        calc = TrajectoryCalc(ammo)
        data = calc.trajectory(weapon, atmosphere, shot_info, wind)

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


class TestPerformance(unittest.TestCase):
    def setUp(self) -> None:
        self.dm = DragModel(0.223, TableG7, 168, 0.308)
        self.ammo = Ammo(self.dm, 1.282, 2750)
        self.weapon = Weapon(2, 100, 11.24)
        self.atmo = Atmo.icao()
        self.shot = Shot(Distance.Yard(1000),
                         Distance.Yard(100),
                         sight_angle=Angular.MOA(4.221)
                         )
        self.wind = [Wind(Velocity(5, Velocity.MPH), -45)]

        self.calc = TrajectoryCalc(self.ammo)

    def test__init__(self):
        self.assertTrue(self.calc)

    def test_elevation_performance(self):
        self.calc.sight_angle(self.weapon, self.atmo)

    def test_path_performance(self):
        self.calc.trajectory(self.weapon, self.atmo, self.shot, self.wind)


def test_back_n_forth(test, value, units):
    u = test.unit_class(value, units)
    v = u >> units
    test.assertAlmostEqual(v, value, 7, f'Read back failed for {units}')


class TestAngular(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Angular
        self.unit_list = [
            Angular.Degree,
            Angular.MOA,
            Angular.MRad,
            Angular.Mil,
            Angular.Radian,
            Angular.Thousand
        ]

    def test_angular(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestDistance(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Distance
        self.unit_list = [
            Distance.Centimeter,
            Distance.Foot,
            Distance.Inch,
            Distance.Kilometer,
            Distance.Line,
            Distance.Meter,
            Distance.Millimeter,
            Distance.Mile,
            Distance.NauticalMile,
            Distance.Yard
        ]

    def test_distance(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestEnergy(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Energy
        self.unit_list = [
            Energy.FootPound,
            Energy.Joule
        ]

    def test_energy(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestPressure(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Pressure
        self.unit_list = [
            Pressure.Bar,
            Pressure.HP,
            Pressure.MmHg,
            Pressure.InHg
        ]

    def test_pressure(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Temperature
        self.unit_list = [
            Temperature.Fahrenheit,
            Temperature.Kelvin,
            Temperature.Celsius,
            Temperature.Rankin
        ]

    def test_temperature(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Velocity
        self.unit_list = [
            Velocity.FPS,
            Velocity.KMH,
            Velocity.KT,
            Velocity.MPH,
            Velocity.MPS
        ]

    def test_velocity(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestWeight(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Weight
        self.unit_list = [
            Weight.Grain,
            Weight.Gram,
            Weight.Kilogram,
            Weight.Newton,
            Weight.Ounce,
            Weight.Pound
        ]

    def test_weight(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestUnitConversionSyntax(unittest.TestCase):

    def setUp(self) -> None:
        self.low = Distance.Yard(10)
        self.high = Distance.Yard(100)

    def test__eq__(self):
        self.assertEqual(self.low, 360)
        self.assertEqual(360, self.low)
        self.assertEqual(self.low, self.low)
        self.assertEqual(self.low, Distance.Foot(30))

    def test__ne__(self):
        self.assertNotEqual(Distance.Yard(100), Distance.Yard(90))

    def test__lt__(self):
        self.assertLess(self.low, self.high)
        self.assertLess(10, self.high)
        self.assertLess(self.low, 9999)

    def test__gt__(self):
        self.assertGreater(self.high, self.low)
        self.assertGreater(self.high, 10)
        self.assertGreater(9000, self.low)

    def test__ge__(self):
        self.assertGreaterEqual(self.high, self.low)
        self.assertGreaterEqual(self.high, self.high)

        self.assertGreaterEqual(self.high, 90)
        self.assertGreaterEqual(self.high, 0)

    def test__le__(self):
        self.assertLessEqual(self.low, self.high)
        self.assertLessEqual(self.high, self.high)

        self.assertLessEqual(self.low, 360)
        self.assertLessEqual(self.low, 360)

    def test__rshift__(self):
        self.assertIsInstance(self.low >> Distance.Meter, (int, float))
        self.low >>= Distance.Meter
        self.assertIsInstance(self.low, (int, float))

    def test__lshift__(self):
        desired_unit_type = Distance
        desired_units = Distance.Foot
        converted = self.low << desired_units
        self.assertIsInstance(converted, desired_unit_type)
        self.assertEqual(converted.units, desired_units)
        self.low <<= desired_units
        self.assertEqual(self.low.units, desired_units)


if __name__ == '__main__':
    unittest.main()
