from py_ballisticcalc.tools import CramerSpeedOfSound, PejsaTrajectoryCalculator
from py_ballisticcalc.bmath import unit
import math
import unittest


class TestCramer(unittest.TestCase):
    def test_at_atmosphere(self):
        c = CramerSpeedOfSound.at_atmosphere(
            unit.Temperature(15, unit.TemperatureCelsius),
            unit.Pressure(760, unit.PressureMmHg),
            50
        )
        self.assertLess(math.fabs(340.8798 - self._c(15)), 1e-3)
        self.assertLess(math.fabs(347.7632 - self._c(26)), 1e-3)
        self.assertLess(math.fabs(312.7595 - self._c(-30)), 1e-3)

    @staticmethod
    def _c(t):
        c = CramerSpeedOfSound.at_atmosphere(
            unit.Temperature(t, unit.TemperatureCelsius),
            unit.Pressure(760, unit.PressureMmHg),
            humidity=50
        )
        return c
