import math
import unittest
from py_ballisticcalc.bmath import unit


def test_back_n_forth(test, value, units):
    u = test.unit_class(value, units)

    test.assertEqual(u.error, None, f'Creation failed for {units}')

    v, err = u.value(units)
    test.assertEqual(err, None, f'Read back failed for {units}')
    test.assertLess(math.fabs(v - value), 1e-7, f'Read back failed for {units}')
    test.assertLess(math.fabs(v - u.get_in(units)), 1e-7, f'Read back failed for {units}')


class TestAngular(unittest.TestCase):

    def setUp(self) -> None:
        self.unit_class = unit.Angular

    def test_degree(self):
        test_back_n_forth(self, 3, unit.AngularDegree)

    def test_moa(self):
        test_back_n_forth(self, 3, unit.AngularMOA)

    def test_mrad(self):
        test_back_n_forth(self, 3, unit.AngularMRad)

    def test_mil(self):
        test_back_n_forth(self, 3, unit.AngularMil)

    def test_radian(self):
        test_back_n_forth(self, 3, unit.AngularRadian)

    def test_thousand(self):
        test_back_n_forth(self, 3, unit.AngularThousand)


class TestDistance(unittest.TestCase):

    def setUp(self) -> None:
        self.unit_class = unit.Distance

    def test_centimeter(self):
        test_back_n_forth(self, 3, unit.DistanceCentimeter)

    def test_foot(self):
        test_back_n_forth(self, 3, unit.DistanceFoot)

    def test_inch(self):
        test_back_n_forth(self, 3, unit.DistanceInch)

    def test_kilometer(self):
        test_back_n_forth(self, 3, unit.DistanceKilometer)

    def test_line(self):
        test_back_n_forth(self, 3, unit.DistanceLine)

    def test_meter(self):
        test_back_n_forth(self, 3, unit.DistanceMeter)

    def test_miles(self):
        test_back_n_forth(self, 3, unit.DistanceMile)

    def test_millimeter(self):
        test_back_n_forth(self, 3, unit.DistanceMillimeter)

    def test_nautical_mile(self):
        test_back_n_forth(self, 3, unit.DistanceNauticalMile)

    def test_yard(self):
        test_back_n_forth(self, 3, unit.DistanceYard)


class TestEnergy(unittest.TestCase):

    def setUp(self) -> None:
        self.unit_class = unit.Energy

    def test_foot_pounds(self):
        test_back_n_forth(self, 3, unit.EnergyFootPound)

    def test_joule(self):
        test_back_n_forth(self, 3, unit.EnergyJoule)


class TestPressure(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Pressure

    def test_bar(self):
        test_back_n_forth(self, 3, unit.PressureBar)

    def test_hp(self):
        test_back_n_forth(self, 3, unit.PressureHP)

    def test_mmhg(self):
        test_back_n_forth(self, 3, unit.PressureMmHg)

    def test_inhg(self):
        test_back_n_forth(self, 3, unit.PressureInHg)


class TestTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Temperature

    def test_F(self):
        test_back_n_forth(self, 3, unit.TemperatureFahrenheit)

    def test_C(self):
        test_back_n_forth(self, 3, unit.TemperatureCelsius)

    def test_K(self):
        test_back_n_forth(self, 3, unit.TemperatureKelvin)

    def test_R(self):
        test_back_n_forth(self, 3, unit.TemperatureRankin)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Velocity

    def test_fps(self):
        test_back_n_forth(self, 3, unit.VelocityFPS)

    def test_kmh(self):
        test_back_n_forth(self, 3, unit.VelocityKMH)

    def test_kt(self):
        test_back_n_forth(self, 3, unit.VelocityKT)

    def test_mph(self):
        test_back_n_forth(self, 3, unit.VelocityMPH)

    def test_mps(self):
        test_back_n_forth(self, 3, unit.VelocityMPS)


class TestWeight(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = unit.Weight

    def test_grain(self):
        test_back_n_forth(self, 3, unit.WeightGrain)

    def test_gram(self):
        test_back_n_forth(self, 3, unit.WeightGram)

    def test_kilogram(self):
        test_back_n_forth(self, 3, unit.WeightKilogram)

    def test_newton(self):
        test_back_n_forth(self, 3, unit.WeightNewton)

    def test_ounce(self):
        test_back_n_forth(self, 3, unit.WeightOunce)

    def test_pound(self):
        test_back_n_forth(self, 3, unit.WeightPound)


if __name__ == '__main__':
    unittest.main()
