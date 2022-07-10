import timeit
import unittest
import pyximport; pyximport.install()
from py_ballisticcalc.bmath.cunit.energy import *
from py_ballisticcalc.bmath.cunit.temperature import *
from py_ballisticcalc.bmath.cunit.pressure import *
from py_ballisticcalc.bmath.cunit.velocity import *
from py_ballisticcalc.bmath.cunit.weight import *
from py_ballisticcalc.bmath.cunit.angular import *
from py_ballisticcalc.bmath.cunit.distance import *


class TestEnergy(unittest.TestCase):

    def test_create(self):
        v = Energy(10, EnergyFootPound)
        v.get_in(EnergyJoule)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestTemperature(unittest.TestCase):

    def test_create(self):
        v = Temperature(15, TemperatureCelsius)
        v.get_in(TemperatureFahrenheit)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestPressure(unittest.TestCase):

    def test_create(self):
        v = Pressure(760, PressureMmHg)
        v.get_in(PressureBar)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestVelocity(unittest.TestCase):

    def test_create(self):
        v = Velocity(800, VelocityMPS)
        v.get_in(VelocityFPS)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestWeight(unittest.TestCase):

    def test_create(self):
        v = Weight(800, WeightGrain)
        v.get_in(WeightGram)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestAngular(unittest.TestCase):

    def test_create(self):
        v = Angular(800, AngularMOA)
        v.get_in(AngularMil)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)


class TestDistance(unittest.TestCase):

    def test_create(self):
        v = Distance(800, DistanceMeter)
        v.get_in(DistanceFoot)

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=50000)
        print(t)
