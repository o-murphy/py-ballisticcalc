import math
import unittest
from py_ballisticcalc.bmath import unit


def test_back_n_forth(test, value, units):
    u = test.unit_class(value, units)
    test.assertEqual(u.error, None, f'Creation failed for {units}')

    v, err = u.value(units)
    test.assertTrue(
        err is None
        and math.fabs(v - value) < 1e-7
        and math.fabs(v - u.get_in(units) < 1e-7), f'Read back failed for {units}')


class TestAngular(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Angular
        self.unit_list = [
            unit.AngularDegree,
            unit.AngularMOA,
            unit.AngularMRad,
            unit.AngularMil,
            unit.AngularRadian,
            unit.AngularThousand
        ]

    def test_angular(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestDistance(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Distance
        self.unit_list = [
            unit.DistanceCentimeter,
            unit.DistanceFoot,
            unit.DistanceInch,
            unit.DistanceKilometer,
            unit.DistanceLine,
            unit.DistanceMeter,
            unit.DistanceMillimeter,
            unit.DistanceMile,
            unit.DistanceNauticalMile,
            unit.DistanceYard
        ]

    def test_distance(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestEnergy(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Energy
        self.unit_list = [
            unit.EnergyFootPound,
            unit.EnergyJoule
        ]

    def test_energy(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestPressure(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Pressure
        self.unit_list = [
            unit.PressureBar,
            unit.PressureHP,
            unit.PressureMmHg,
            unit.PressureInHg
        ]

    def test_pressure(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Temperature
        self.unit_list = [
            unit.TemperatureFahrenheit,
            unit.TemperatureKelvin,
            unit.TemperatureCelsius,
            unit.TemperatureRankin
        ]

    def test_temperature(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Velocity
        self.unit_list = [
            unit.VelocityFPS,
            unit.VelocityKMH,
            unit.VelocityKT,
            unit.VelocityMPH,
            unit.VelocityMPS
        ]

    def test_velocity(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


class TestWeight(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Weight
        self.unit_list = [
            unit.WeightGrain,
            unit.WeightGram,
            unit.WeightKilogram,
            unit.WeightNewton,
            unit.WeightOunce,
            unit.WeightPound
        ]

    def test_weight(self):
        for u in self.unit_list:
            with self.subTest(unit=unit):
                test_back_n_forth(self, 3, u)


if __name__ == '__main__':
    unittest.main()
