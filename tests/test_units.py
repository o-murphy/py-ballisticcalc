import unittest
from dataclasses import dataclass

from py_ballisticcalc.unit import *


def back_n_forth(test, value, units):
    u = test.unit_class(value, units)
    v = u >> units
    test.assertAlmostEqual(v, value, 7, f'Read back failed for {units}')


class TestPrefUnits(unittest.TestCase):

    def test_pref(self):
        @dataclass
        class TestClass(PreferredUnits.Mixin):
            as_metadata_str: [float, Distance] = Dimension(prefer_units='sight_height')
            as_metadata_unit: [float, Distance] = Dimension(prefer_units=Unit.Meter)

        tc1 = TestClass(1, 1)
        self.assertEqual(tc1.as_metadata_str.units, Unit.Inch)
        self.assertEqual(tc1.as_metadata_unit.units, Unit.Meter)

        tc2 = TestClass(Unit.Meter(1), Unit.Meter(1))
        self.assertEqual(tc2.as_metadata_str.units, Unit.Meter)
        self.assertEqual(tc2.as_metadata_unit.units, Unit.Meter)

        PreferredUnits.sight_height = Unit.Centimeter

        tc3 = TestClass(1, 1)
        self.assertEqual(tc3.as_metadata_str.units, Unit.Centimeter)
        self.assertEqual(tc3.as_metadata_unit.units, Unit.Meter)


class TestUnitsParser(unittest.TestCase):
    def test_parse_values(self):

        valid_cases = [
            '10', '10.2', '.2', '0.', '10ft*lb', '10footpound'
        ]

        for case in valid_cases:

            with self.subTest(case):
                ret = Unit.parse_value(case, Unit.FootPound)
                self.assertIsInstance(ret, Energy)
                self.assertEqual(ret.units, Unit.FootPound)

            with self.subTest(case):
                ret = Unit.parse_value(case, 'footpound')
                self.assertIsInstance(ret, Energy)
                self.assertEqual(ret.units, Unit.FootPound)

            with self.subTest(case):
                ret = Unit.parse_value(case, 'ft*lb')
                self.assertIsInstance(ret, Energy)
                self.assertEqual(ret.units, Unit.FootPound)

            with self.subTest(case):
                ret = Unit.parse_value(case, 'energy')
                self.assertIsInstance(ret, Energy)
                self.assertEqual(ret.units, Unit.FootPound)

    def test_parse_units(self):

        ret = Unit.parse_unit('ft*lb')
        self.assertIsInstance(ret, Unit)


class TestAngular(unittest.TestCase):

    def setUp(self) -> None:
        self.unit_class = Angular
        self.unit_list = [
            Angular.Degree,
            Angular.MOA,
            Angular.MRad,
            Angular.Mil,
            Angular.Radian,
            Angular.Thousandth
        ]

    def test_angular(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                back_n_forth(self, 3, u)

    def test_angle_truncation(self):
        self.assertAlmostEqual(Angular(720, Angular.Degree), Angular(0, Angular.Degree))


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
                back_n_forth(self, 3, u)


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
                back_n_forth(self, 3, u)


class TestPressure(unittest.TestCase):

    def setUp(self) -> None:
        self.unit_class = Pressure
        self.unit_list = [
            Pressure.Bar,
            Pressure.hPa,
            Pressure.MmHg,
            Pressure.InHg
        ]

    def test_pressure(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                back_n_forth(self, 3, u)


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
                back_n_forth(self, 3, u)


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
                back_n_forth(self, 3, u)


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
                back_n_forth(self, 3, u)


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
