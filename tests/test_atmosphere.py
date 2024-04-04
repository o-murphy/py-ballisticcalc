import unittest
from py_ballisticcalc import Atmo
from py_ballisticcalc.unit import *

class TestAtmosphere(unittest.TestCase):
    """Unittests of the Atmosphere class"""

    def setUp(self):
        self.standard = Atmo.standard()
        self.highICAO = Atmo.standard(Distance.Foot(10000))
        self.highISA = Atmo.standard(Distance.Meter(1000))
        self.custom = Atmo(temperature=Temperature.Fahrenheit(30), pressure=Pressure.InHg(31), humidity=0.5)

    def test_standard(self):
        self.assertAlmostEqual(self.standard.temperature >> Temperature.Fahrenheit, 59.0, places=1)
        self.assertAlmostEqual(self.standard.pressure >> Pressure.hPa, 1013.25, places=1)
        self.assertAlmostEqual(self.standard.density_imperial, 0.076474, places=4)

    def test_high(self):
        # Ref https://www.engineeringtoolbox.com/standard-atmosphere-d_604.html
        self.assertAlmostEqual(self.highICAO.temperature >> Temperature.Fahrenheit, 23.36, places=1)
        self.assertAlmostEqual(self.highICAO.density_ratio, 0.7387, places=3)
        # Ref https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html
        self.assertAlmostEqual(self.highISA.pressure >> Pressure.hPa, 899, places=0)
        self.assertAlmostEqual(self.highISA.density_ratio, 0.9075, places=4)

    def test_mach(self):
        # Ref https://www.omnicalculator.com/physics/speed-of-sound
        self.assertAlmostEqual(Atmo.machF(59), 1116.15, places=0)
        self.assertAlmostEqual(Atmo.machF(10), 1062.11, places=0)
        self.assertAlmostEqual(Atmo.machF(99), 1158.39, places=0)
        self.assertAlmostEqual(Atmo.machC(-20), 318.94, places=1)
        self.assertAlmostEqual(self.highISA.mach >> Velocity.MPS, 336.4, places=1)


if __name__ == '__main__':
    unittest.main()
