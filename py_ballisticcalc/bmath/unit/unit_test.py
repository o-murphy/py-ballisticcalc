import unittest
import pyximport
pyximport.install()
from py_ballisticcalc.bmath.unit import *

import math


def test_back_n_forth(test, value, units):
    u = test.unit_class(value, units)
    v = u.value(units)
    test.assertTrue(
        math.fabs(v - value) < 1e-7
        and math.fabs(v - u.get_in(units) < 1e-7), f'Read back failed for {units}')


class TestAngular(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Angular
        self.unit_list = [
            AngularDegree,
            AngularMOA,
            AngularMRad,
            AngularMil,
            AngularRadian,
            AngularThousand
        ]

    def test_angular(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestDistance(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Distance
        self.unit_list = [
            DistanceCentimeter,
            DistanceFoot,
            DistanceInch,
            DistanceKilometer,
            DistanceLine,
            DistanceMeter,
            DistanceMillimeter,
            DistanceMile,
            DistanceNauticalMile,
            DistanceYard
        ]

    def test_distance(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestEnergy(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Energy
        self.unit_list = [
            EnergyFootPound,
            EnergyJoule
        ]

    def test_energy(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestPressure(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Pressure
        self.unit_list = [
            PressureBar,
            PressureHP,
            PressureMmHg,
            PressureInHg
        ]

    def test_pressure(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Temperature
        self.unit_list = [
            TemperatureFahrenheit,
            TemperatureKelvin,
            TemperatureCelsius,
            TemperatureRankin
        ]

    def test_temperature(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Velocity
        self.unit_list = [
            VelocityFPS,
            VelocityKMH,
            VelocityKT,
            VelocityMPH,
            VelocityMPS
        ]

    def test_velocity(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestWeight(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Weight
        self.unit_list = [
            WeightGrain,
            WeightGram,
            WeightKilogram,
            WeightNewton,
            WeightOunce,
            WeightPound
        ]

    def test_weight(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


if __name__ == '__main__':
    unittest.main()
