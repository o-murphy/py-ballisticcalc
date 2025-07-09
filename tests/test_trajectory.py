"""Unittests for the py_ballisticcalc library"""

from math import fabs

import pytest

from py_ballisticcalc import *


class TestTrajectory:

    def test_zero1(self, loaded_engine_instance):
        dm = DragModel(0.365, TableG1, 69, 0.223, 0.9)
        ammo = Ammo(dm, 2600)
        weapon = Weapon(Distance(3.2, Distance.Inch))
        atmosphere = Atmo.icao()
        calc = Calculator(engine=loaded_engine_instance)
        zero_angle = calc.barrel_elevation_for_target(Shot(weapon=weapon, ammo=ammo, atmo=atmosphere),
                                                      Distance(100, Distance.Yard))
        assert pytest.approx(zero_angle >> Angular.Radian, abs=1e-4) == 0.0016514

    def test_zero2(self, loaded_engine_instance):
        dm = DragModel(0.223, TableG7, 69, 0.223, 0.9)
        ammo = Ammo(dm, 2750)
        weapon = Weapon(Distance(2, Distance.Inch))
        atmosphere = Atmo.icao()
        calc = Calculator(engine=loaded_engine_instance)
        zero_angle = calc.barrel_elevation_for_target(Shot(weapon=weapon, ammo=ammo, atmo=atmosphere),
                                                      Distance(100, Distance.Yard))
        assert pytest.approx(zero_angle >> Angular.Radian, abs=1e-4) == 0.0012286

    def custom_assert_equal(self, a, b, accuracy, name):
        assert fabs(a - b) < accuracy, f'Equality {name} failed (|{a} - {b}|, {accuracy} digits)'

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float,
                     mach: float, energy: float, path: float, hold: float,
                     windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: Unit):

        self.custom_assert_equal(distance, data.distance >> Distance.Yard, 0.1, "Distance")
        self.custom_assert_equal(velocity, data.velocity >> Velocity.FPS, 5, "Velocity")
        self.custom_assert_equal(mach, data.mach, 0.005, "Mach")
        self.custom_assert_equal(energy, data.energy >> Energy.FootPound, 5, "Energy")
        self.custom_assert_equal(time, data.time, 0.06, "Time")
        self.custom_assert_equal(ogv, data.ogw >> Weight.Pound, 1, "OGV")

        if distance >= 800:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 4, 'Drop')
        elif distance >= 500:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 1, 'Drop')
        else:
            self.custom_assert_equal(path, data.height >> Distance.Inch, 0.5, 'Drop')

        if distance > 1:
            self.custom_assert_equal(hold, data.drop_adj >> adjustment_unit, 0.5, 'Hold')

        if distance >= 800:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1.5, "Windage")
        elif distance >= 500:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 1, "Windage")
        else:
            self.custom_assert_equal(windage, data.windage >> Distance.Inch, 0.5, "Windage")

        if distance > 1:
            self.custom_assert_equal(wind_adjustment,
                                     data.windage_adj >> adjustment_unit, 0.5, "WAdj")

    @pytest.mark.parametrize(
        "data_point, distance, velocity, mach, energy, path, hold, windage, wind_adjustment, time, ogv, adjustment_unit",
        [
            (lambda trajectory: trajectory[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, Angular.MOA),
            (lambda trajectory: trajectory[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, Angular.MOA),
            (lambda trajectory: trajectory[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, Angular.MOA),
            (lambda trajectory: trajectory[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, Angular.MOA),
        ],
        ids=["0_yards", "100_yards", "500_yards", "1000_yards"]
    )
    def test_path_g1(self, loaded_engine_instance, data_point, distance, velocity, mach, energy, path, hold, windage,
                     wind_adjustment, time, ogv, adjustment_unit):
        dm = DragModel(0.223, TableG1, 168, 0.308, 1.282)
        ammo = Ammo(dm, Velocity(2750, Velocity.FPS))
        weapon = Weapon(Distance(2, Distance.Inch), zero_elevation=Angular(0.001228, Angular.Radian))
        atmosphere = Atmo.icao()
        shot_info = Shot(weapon=weapon, ammo=ammo, atmo=atmosphere,
                         winds=[Wind(Velocity(5, Velocity.MPH), Angular(10.5, Angular.OClock))])

        calc = Calculator(engine=loaded_engine_instance)
        data = calc.fire(shot_info, Distance.Yard(1000), Distance.Yard(100)).trajectory
        assert len(data) == 11, "Trajectory Row Count"
        self.validate_one(data_point(data), distance, velocity, mach, energy, path, hold, windage, wind_adjustment,
                          time, ogv, adjustment_unit)

    @pytest.mark.parametrize(
        "data_point, distance, velocity, mach, energy, path, hold, windage, wind_adjustment, time, ogv, adjustment_unit",
        [
            (lambda trajectory: trajectory[0], 0, 2750, 2.46, 2821, -2.0, 0.0, 0.0, 0.00, 0.000, 880, Angular.Mil),
            (lambda trajectory: trajectory[1], 100, 2545, 2.28, 2416, 0.0, 0.0, -0.2, -0.06, 0.113, 698, Angular.Mil),
            (lambda trajectory: trajectory[5], 500, 1814, 1.62, 1227, -56.2, -3.2, -6.3, -0.36, 0.672, 252, Angular.Mil),
            (lambda trajectory: trajectory[10], 1000, 1086, 0.97, 440, -399.9, -11.3, -31.6, -0.90, 1.748, 54, Angular.Mil)
        ],
        ids=["0_yards", "100_yards", "500_yards", "1000_yards"]
    )
    def test_path_g7(self, loaded_engine_instance, data_point, distance, velocity, mach, energy, path, hold, windage,
                     wind_adjustment, time, ogv, adjustment_unit):
        dm = DragModel(0.223, TableG7, 168, 0.308, 1.282)
        ammo = Ammo(dm, Velocity(2750, Velocity.FPS))
        weapon = Weapon(2, 12, zero_elevation=Angular.MOA(4.221))
        shot_info = Shot(weapon=weapon, ammo=ammo, winds=[Wind(Velocity(5, Velocity.MPH), Angular.Degree(-45))])

        calc = Calculator(engine=loaded_engine_instance)
        data = calc.fire(shot_info, Distance.Yard(1000), Distance.Yard(100)).trajectory
        assert len(data) == 11, "Trajectory Row Count"
        self.validate_one(data_point(data), distance, velocity, mach, energy, path, hold, windage, wind_adjustment,
                          time, ogv, adjustment_unit)
