import unittest

from py_ballisticcalc.projectile import *
from py_ballisticcalc.drag import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.trajectory_calculator import *
from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.trajectory_data import *
from py_ballisticcalc.shot_parameters import *
from py_ballisticcalc.bmath import unit


class TestPyBallisticCalc(unittest.TestCase):

    def test_zero1(self):
        bc = BallisticCoefficient(0.365, DragTableG1)
        projectile = Projectile(bc, unit.Weight(69, unit.WeightGrain).validate())
        ammo = Ammunition(projectile, unit.Velocity(2600, unit.VelocityFPS).validate())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).validate())
        weapon = Weapon(unit.Distance(3.2, unit.DistanceInch).validate(), zero)
        atmosphere = Atmosphere()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(math.fabs(sight_angle.get_in(unit.AngularRadian) - 0.001651), 1e-6,
                        f'TestZero1 failed {sight_angle.get_in(unit.AngularRadian):.10f}')

    def test_zero2(self):
        bc = BallisticCoefficient(0.223, DragTableG7)
        projectile = Projectile(bc, unit.Weight(168, unit.WeightGrain).validate())
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS).validate())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).validate())
        weapon = Weapon(unit.Distance(2, unit.DistanceInch).validate(), zero)
        atmosphere = Atmosphere()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(math.fabs(sight_angle.get_in(unit.AngularRadian) - 0.001228), 1e-6,
                        f'TestZero2 failed {sight_angle.get_in(unit.AngularRadian):.10f}')

    def assertEqualCustom(self, a, b, accuracy, name):
        with self.subTest():
            self.assertFalse(math.fabs(a - b) > accuracy, f'Assertion {name} failed ({a}/{b})')

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float, mach: float, energy: float,
                     path: float, hold: float, windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: int):

        self.assertEqualCustom(distance, data.travelled_distance.get_in(unit.DistanceYard), 0.001, "Distance")
        self.assertEqualCustom(velocity, data.velocity.get_in(unit.VelocityFPS), 5, "Velocity")
        self.assertEqualCustom(mach, data.mach_velocity, 0.005, "Mach")
        self.assertEqualCustom(energy, data.energy.get_in(unit.EnergyFootPound), 5, "Energy")
        self.assertEqualCustom(time, data.time.total_seconds, 0.06, "Time")
        self.assertEqualCustom(ogv, data.optimal_game_weight.get_in(unit.WeightPound), 1, "OGV")

        if distance >= 800:
            self.assertEqualCustom(path, data.drop.get_in(unit.DistanceInch), 4, 'Drop')
        elif distance >= 500:
            self.assertEqualCustom(path, data.drop.get_in(unit.DistanceInch), 1, 'Drop')
        else:
            self.assertEqualCustom(path, data.drop.get_in(unit.DistanceInch), 0.5, 'Drop')

        if distance > 1:
            self.assertEqualCustom(hold, data.drop_adjustment.get_in(adjustment_unit), 0.5, 'Hold')

        if distance >= 800:
            self.assertEqualCustom(windage, data.windage.get_in(unit.DistanceInch), 1.5, "Windage")
        elif distance >= 500:
            self.assertEqualCustom(windage, data.windage.get_in(unit.DistanceInch), 1, "Windage")
        else:
            self.assertEqualCustom(windage, data.windage.get_in(unit.DistanceInch), 0.5, "Windage")

        if distance > 1:
            self.assertEqualCustom(wind_adjustment, data.windage_adjustment.get_in(adjustment_unit), 0.5, "WAdj")

    def test_path_g1(self):
        bc = BallisticCoefficient(0.223, DragTableG1)
        projectile = Projectile(bc, unit.Weight(168, unit.WeightGrain).validate())
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS).validate())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).validate())
        weapon = Weapon(unit.Distance(2, unit.DistanceInch).validate(), zero)
        atmosphere = Atmosphere()
        shot_info = ShotParameters(unit.Angular(0.001228, unit.AngularRadian).validate(),
                                   unit.Distance(1000, unit.DistanceYard).validate(),
                                   unit.Distance(100, unit.DistanceYard).validate())
        wind = WindInfo.create_only_wind_info(unit.Velocity(5, unit.VelocityMPH).validate(),
                                              unit.Angular(-45, unit.AngularDegree).validate())

        calc = TrajectoryCalculator()
        data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

        self.assertEqualCustom(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.AngularMOA],
            [data[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, unit.AngularMOA],
            [data[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, unit.AngularMOA],
            [data[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, unit.AngularMOA]
        ]

        for d in test_data:
            with self.subTest():
                self.validate_one(*d)

    def test_path_g7(self):
        bc = BallisticCoefficient(0.223, DragTableG7)
        projectile = ProjectileWithDimensions(bc, unit.Distance(0.308, unit.DistanceInch).validate(),
                                              unit.Distance(1.282, unit.DistanceInch).validate(),
                                              unit.Weight(168, unit.WeightGrain).validate())
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS).validate())
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard).validate())
        twist = TwistInfo(TwistRight, unit.Distance(11.24, unit.DistanceInch).validate())
        weapon = Weapon.create_with_twist(unit.Distance(2, unit.DistanceInch).validate(), zero, twist)
        atmosphere = Atmosphere()
        shot_info = ShotParameters(unit.Angular(4.221, unit.AngularMOA).validate(),
                                   unit.Distance(1000, unit.DistanceYard).validate(),
                                   unit.Distance(100, unit.DistanceYard).validate())
        wind = WindInfo.create_only_wind_info(unit.Velocity(5, unit.VelocityMPH).validate(),
                                              unit.Angular(-45, unit.AngularDegree).validate())

        calc = TrajectoryCalculator()
        data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

        self.assertEqualCustom(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.AngularMil],
            [data[1], 100, 2544.3, 2.279, 2416, 0, 0, -0.35, -0.09, 0.113, 698, unit.AngularMil],
            [data[5], 500, 1810.7, 1.622, 1226, -56.3, -3.18, -9.96, -0.55, 0.673, 252, unit.AngularMil],
            [data[10], 1000, 1081.3, 0.968, 442, -401.6, -11.32, -50.98, -1.44, 1.748, 55, unit.AngularMil]
        ]

        for d in test_data:
            with self.subTest():
                self.validate_one(*d)


if __name__ == '__main__':
    unittest.main()
