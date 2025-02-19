import unittest
from py_ballisticcalc import *

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

    def test_altitude(self):
        # Altitude adjustment not valid above troposphere
        with self.assertWarns(RuntimeWarning):
            Atmo().get_density_factor_and_mach_for_altitude(100_000)

    def test_density(self):
        self.assertAlmostEqual(Atmo.calculate_air_density(20, 1013, 0), 1.20383, places=4)
        self.assertAlmostEqual(Atmo.calculate_air_density(20, 1013, 1), 1.19332, places=4)

    def test_changes(self):
        # Increasing altitude should decrease temperature, pressure, air density, and mach 1 speed
        self.assertLess(self.standard.temperature_at_altitude(5000), self.standard.temperature >> Temperature.Celsius)
        self.assertLess(self.standard.pressure_at_altitude(5000), self.standard.pressure >> Pressure.hPa)
        density_ratio, mach = self.standard.get_density_factor_and_mach_for_altitude(5000)
        self.assertLess(density_ratio, self.standard.density_ratio)
        self.assertLess(mach, self.standard.mach >> Velocity.FPS)

    def test_trajectory_effects(self):
        check_distance = Distance.Yard(1000)
        ammo = Ammo(DragModel(0.22, TableG7), mv=Velocity.FPS(3000))
        weapon = Weapon()
        atmo = Atmo(altitude=0)  # Start with standard sea-level atmosphere
        # Set baseline to zero at 1000 yards
        zero = Shot(weapon=weapon, ammo=ammo, atmo=atmo)
        calc = Calculator()
        calc.set_weapon_zero(zero, check_distance)
        baseline_trajectory = calc.fire(shot=zero, trajectory_range=check_distance, trajectory_step=check_distance)
        baseline = baseline_trajectory.get_at_distance(check_distance)

        # Increasing humidity reduces air density which decreases drag
        atmo.humidity = 1.0
        t_humid = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=atmo), trajectory_range=check_distance, trajectory_step=check_distance)
        self.assertGreater(baseline.time, t_humid.get_at_distance(check_distance).time)

        # Increasing temperature reduces air density which decreases drag
        warm = Atmo(altitude=0, temperature=Temperature.Fahrenheit(120))
        t_warm = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=warm), trajectory_range=check_distance, trajectory_step=check_distance)
        self.assertGreater(baseline.time, t_warm.get_at_distance(check_distance).time)

        # Increasing altitude reduces air density which decreases drag
        high = Atmo(altitude=Distance.Foot(5000))  # simulate increased altitude
        t_high = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=high), trajectory_range=check_distance, trajectory_step=check_distance)
        self.assertGreater(baseline.time, t_high.get_at_distance(check_distance).time)

if __name__ == "__main__":
    unittest.main()