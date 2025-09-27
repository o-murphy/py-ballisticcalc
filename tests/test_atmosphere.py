import pytest

from py_ballisticcalc import *


class TestAtmosphere:
    """Unittests of the Atmosphere class"""

    def setup_method(self):
        self.standard = Atmo.standard()
        self.highICAO = Atmo.standard(Distance.Foot(10000))
        self.highISA = Atmo.standard(Distance.Meter(1000))
        self.custom = Atmo(temperature=Temperature.Fahrenheit(30), pressure=Pressure.InHg(31), humidity=0.5)

    def test_standard(self):
        assert pytest.approx(self.standard.temperature >> Temperature.Fahrenheit, abs=1e-1) == 59.0
        assert pytest.approx(self.standard.pressure >> Pressure.hPa, abs=1e-1) == 1013.25
        assert pytest.approx(self.standard.density_imperial, abs=1e-4) == 0.076474

    def test_high(self):
        # Ref https://www.engineeringtoolbox.com/standard-atmosphere-d_604.html
        assert pytest.approx(self.highICAO.temperature >> Temperature.Fahrenheit, abs=1e-1) == 23.36
        assert pytest.approx(self.highICAO.density_ratio, abs=1e-3) == 0.7387
        # Ref https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html
        assert pytest.approx(self.highISA.pressure >> Pressure.hPa, abs=1e-0) == 899
        assert pytest.approx(self.highISA.density_ratio, abs=1e-4) == 0.9078658

    def test_mach(self):
        # Ref https://www.omnicalculator.com/physics/speed-of-sound
        assert pytest.approx(Atmo.machF(59), abs=1e-0) == 1116.15
        assert pytest.approx(Atmo.machF(10), abs=1e-0) == 1062.11
        assert pytest.approx(Atmo.machF(99), abs=1e-0) == 1158.39
        assert pytest.approx(Atmo.machC(-20), abs=1e-1) == 318.94
        assert pytest.approx(self.highISA.mach >> Velocity.MPS, abs=1e-1) == 336.4

    def test_atmo_mach_warning_paths(self):
        # Request sound speed for temperatures below absolute zero
        with pytest.warns(RuntimeWarning):
            _ = Atmo.machF(-1000.0)
        with pytest.warns(RuntimeWarning):
            _ = Atmo.machC(-1000.0)

    def test_altitude_limit(self):
        with pytest.warns(RuntimeWarning):
            # Altitude adjustment not valid above troposphere
            d, m = Atmo().get_density_and_mach_for_altitude(100_000)
            assert d > 0 and m > 0

    def test_temperature_limit(self):
        a = Atmo.icao()
        with pytest.warns(RuntimeWarning):
            # Very low temperature via interpolation to extreme altitude
            t = a.temperature_at_altitude(1e9)
            assert t > -273.15

    def test_density(self):
        assert pytest.approx(Atmo.calculate_air_density(20, 1013, 0), abs=1e-4) == 1.20426
        assert pytest.approx(Atmo.calculate_air_density(20, 1013, 1), abs=1e-4) == 1.1937899

    def test_changes(self):
        # Increasing altitude should decrease temperature, pressure, air density, and mach 1 speed
        assert self.standard.temperature_at_altitude(5000) < (self.standard.temperature >> Temperature.Celsius)
        assert self.standard.pressure_at_altitude(5000) < (self.standard.pressure >> Pressure.hPa)
        density_ratio, mach = self.standard.get_density_and_mach_for_altitude(5000)
        assert density_ratio < self.standard.density_ratio
        assert mach < (self.standard.mach >> Velocity.FPS)

    def test_vacuum(self):
        vac = Vacuum(altitude=Distance.Foot(0))
        assert vac.density_ratio == 0
        assert vac.mach.raw_value > 0

    def test_atmo_density_and_mach_accessors(self):
        atmo = Atmo.icao(altitude=Distance.Foot(1000))
        dr, m = atmo.get_density_and_mach_for_altitude(1500.0)
        assert 0 < dr <= 2
        assert m > 0
        # Set humidity and verify update
        atmo.humidity = 50
        assert pytest.approx(atmo.humidity, abs=1e-9) == 0.5

    def test_wind_vector_and_shot_winds_sorting(self):
        w1 = Wind(velocity=Velocity.FPS(10), direction_from=Angular.Degree(90), until_distance=Distance.Foot(10))
        w2 = Wind(velocity=Velocity.FPS(5), direction_from=Angular.Degree(0), until_distance=Distance.Foot(5))
        dm = DragModel(bc=0.2, drag_table=TableG7, diameter=Distance.Millimeter(7.0), length=Distance.Millimeter(30.0), weight=Weight.Grain(150))
        ammo = Ammo(dm, mv=Velocity.FPS(2500))
        shot = Shot(ammo=ammo)
        shot.winds = [w1, w2]
        # Winds are sorted by until_distance
        assert shot.winds[0].until_distance.raw_value <= shot.winds[1].until_distance.raw_value
        # Vector basic sanity
        v = w1.vector
        assert isinstance(v.x, float) and isinstance(v.z, float)

    def test_trajectory_effects(self, loaded_engine_instance):
        check_distance = Distance.Yard(1000)
        ammo = Ammo(DragModel(0.22, TableG7), mv=Velocity.FPS(3000))
        weapon = Weapon()
        atmo = Atmo(altitude=0)  # Start with standard sea-level atmosphere
        # Set baseline to zero at 1000 yards
        zero = Shot(weapon=weapon, ammo=ammo, atmo=atmo)
        calc = Calculator(engine=loaded_engine_instance)
        calc.set_weapon_zero(zero, check_distance)
        baseline_trajectory = calc.fire(shot=zero, trajectory_range=check_distance, trajectory_step=check_distance)
        baseline = baseline_trajectory.get_at('distance', check_distance, epsilon=1e-8)

        # Increasing humidity reduces air density which decreases drag
        atmo.humidity = 1.0
        t_humid = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=atmo), trajectory_range=check_distance,
                            trajectory_step=check_distance)
        assert t_humid.get_at('distance', check_distance, epsilon=1e-8).time < baseline.time

        # Increasing temperature reduces air density which decreases drag
        warm = Atmo(altitude=0, temperature=Temperature.Fahrenheit(120))
        t_warm = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=warm), trajectory_range=check_distance,
                           trajectory_step=check_distance)
        assert t_warm.get_at('distance', check_distance, epsilon=1e-8).time < baseline.time

        # Increasing altitude reduces air density which decreases drag
        high = Atmo(altitude=Distance.Foot(5000))  # simulate increased altitude
        t_high = calc.fire(Shot(weapon=weapon, ammo=ammo, atmo=high), trajectory_range=check_distance,
                           trajectory_step=check_distance)
        assert t_high.get_at('distance', check_distance, epsilon=1e-8).time < baseline.time