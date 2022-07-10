import timeit
import unittest
import pyximport; pyximport.install()
from py_ballisticcalc.extended.bin.atmosphere import *


class TestAtmo(unittest.TestCase):

    def test_create(self):
        v = Atmosphere(
            altitude=Distance(0, DistanceMeter),
            pressure=Pressure(760, PressureMmHg),
            temperature=Temperature(15, TemperatureCelsius),
            humidity=0.5
        )

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(t)
