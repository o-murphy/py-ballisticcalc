import timeit
from datetime import datetime
import unittest
import pyximport

from math import fabs

pyximport.install()
from py_ballisticcalc.lib.atmosphere import Atmosphere, IcaoAtmosphere
from py_ballisticcalc.lib.drag import BallisticCoefficient, DragTableG1, DragTableG7
from py_ballisticcalc.lib.projectile import Projectile, ProjectileWithDimensions
from py_ballisticcalc.lib.weapon import Ammunition, ZeroInfo, TwistInfo, TwistRight, WeaponWithTwist
from py_ballisticcalc.lib.wind import create_only_wind_info
from py_ballisticcalc.lib.shot_parameters import ShotParameters, ShotParametersUnlevel
from py_ballisticcalc.lib.trajectory_calculator import TrajectoryCalculator
from py_ballisticcalc.lib.bmath import unit as unit
from py_ballisticcalc.lib.bmath.unit import *


class TestAtmo(unittest.TestCase):

    def test_create(self):
        v = Atmosphere(
            altitude=Distance(0, DistanceMeter),
            pressure=Pressure(760, PressureMmHg),
            temperature=Temperature(15, TemperatureCelsius),
            humidity=0.5
        )

        icao = IcaoAtmosphere(Distance(0, DistanceMeter))

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(t)


class TestShotParams(unittest.TestCase):

    def test_create(self):
        v = ShotParameters(
            Angular(0, AngularDegree),
            Distance(1000, DistanceFoot),
            Distance(100, DistanceFoot)
        )

    def test_unlevel(self):
        v = ShotParametersUnlevel(
            Angular(0, AngularDegree),
            Distance(1000, DistanceFoot),
            Distance(100, DistanceFoot),
            Angular(0, AngularDegree),
            Angular(0, AngularDegree)
        )

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))
        t = timeit.timeit(self.test_unlevel, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))


class TestDrag(unittest.TestCase):

    def setUp(self) -> None:
        self.bc = self.test_create()

    def test_create(self):
        bc = BallisticCoefficient(
            value=0.275,
            drag_table=DragTableG7
        )
        return bc

    def test_drag(self):
        return self.bc.drag(3)

    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))
        t = timeit.timeit(self.test_drag, number=50000)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))


class TestG7Profile(unittest.TestCase):

    def test_drag(self):
        bc = BallisticCoefficient(
            value=0.223,
            drag_table=DragTableG7
        )

        print(bc.drag(3))

    def test_create(self):
        bc = BallisticCoefficient(
            value=0.223,
            drag_table=DragTableG7
        )

        p1 = ProjectileWithDimensions(
            bc,
            Distance(0.308, DistanceInch),
            Distance(1.2, DistanceInch),
            Weight(167, WeightGrain),
        )

        ammo = Ammunition(p1, Velocity(800, VelocityMPS))
        atmo = Atmosphere(Distance(0, DistanceMeter), Pressure(760, PressureMmHg),
                          Temperature(15, TemperatureCelsius), 0.5)

        zero = ZeroInfo(Distance(100, DistanceMeter), True, True, ammo, atmo)
        twist = TwistInfo(TwistRight, Distance(11, DistanceInch))
        weapon = WeaponWithTwist(Distance(90, DistanceMillimeter), zero, twist)
        wind = create_only_wind_info(Velocity(0, VelocityMPS), Angular(0, AngularDegree))
        calc = TrajectoryCalculator()
        calc.set_maximum_calculator_step_size(Distance(1, DistanceFoot))
        sight_angle = calc.sight_angle(ammo, weapon, atmo)
        shot_info = ShotParameters(sight_angle, Distance(2500, DistanceMeter), Distance(1, DistanceMeter))
        return calc.trajectory(ammo, weapon, atmo, shot_info, wind)

    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))

class TestPyBallisticCalc(unittest.TestCase):

    def test_zero1(self):
        bc = BallisticCoefficient(0.365, DragTableG1)
        projectile = Projectile(bc, unit.Weight(69, unit.WeightGrain))
        ammo = Ammunition(projectile, unit.Velocity(2600, unit.VelocityFPS))
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard))
        weapon = Weapon(unit.Distance(3.2, unit.DistanceInch), zero)
        atmosphere = IcaoAtmosphere(Distance(0, DistanceMeter))
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle.get_in(unit.AngularRadian) - 0.001651), 1e-6,
                        f'TestZero1 failed {sight_angle.get_in(unit.AngularRadian):.10f}')

    def test_zero2(self):
        bc = BallisticCoefficient(0.223, DragTableG7)
        projectile = Projectile(bc, unit.Weight(168, unit.WeightGrain))
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS))
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard))
        weapon = Weapon(unit.Distance(2, unit.DistanceInch), zero)
        atmosphere = IcaoAtmosphere(Distance(0, DistanceMeter))
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle.get_in(unit.AngularRadian) - 0.001228), 1e-6,
                        f'TestZero2 failed {sight_angle.get_in(unit.AngularRadian):.10f}')

    def assertEqualCustom(self, a, b, accuracy, name):
        with self.subTest():
            self.assertFalse(fabs(a - b) > accuracy, f'Assertion {name} failed ({a}/{b}, {accuracy})')

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float, mach: float, energy: float,
                     path: float, hold: float, windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: int):

        # self.assertEqualCustom(distance, data.travelled_distance().get_in(unit.DistanceYard), 0.001, "Distance")
        self.assertEqualCustom(velocity, data.velocity().get_in(unit.VelocityFPS), 5, "Velocity")
        self.assertEqualCustom(mach, data.mach_velocity(), 0.005, "Mach")
        self.assertEqualCustom(energy, data.energy().get_in(unit.EnergyFootPound), 5, "Energy")
        self.assertEqualCustom(time, data.time().total_seconds(), 0.06, "Time")
        self.assertEqualCustom(ogv, data.optimal_game_weight().get_in(unit.WeightPound), 1, "OGV")

        if distance >= 800:
            self.assertEqualCustom(path, data.drop().get_in(unit.DistanceInch), 4, 'Drop')
        elif distance >= 500:
            self.assertEqualCustom(path, data.drop().get_in(unit.DistanceInch), 1, 'Drop')
        else:
            self.assertEqualCustom(path, data.drop().get_in(unit.DistanceInch), 0.5, 'Drop')

        if distance > 1:
            self.assertEqualCustom(hold, data.drop_adjustment().get_in(adjustment_unit), 0.5, 'Hold')

        if distance >= 800:
            self.assertEqualCustom(windage, data.windage().get_in(unit.DistanceInch), 1.5, "Windage")
        elif distance >= 500:
            self.assertEqualCustom(windage, data.windage().get_in(unit.DistanceInch), 1, "Windage")
        else:
            self.assertEqualCustom(windage, data.windage().get_in(unit.DistanceInch), 0.5, "Windage")

        if distance > 1:
            self.assertEqualCustom(wind_adjustment, data.windage_adjustment().get_in(adjustment_unit), 0.5, "WAdj")

    def test_path_g1(self):
        bc = BallisticCoefficient(0.223, DragTableG1)
        projectile = Projectile(bc, unit.Weight(168, unit.WeightGrain))
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS))
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard))
        weapon = Weapon(unit.Distance(2, unit.DistanceInch), zero)
        atmosphere = IcaoAtmosphere(Distance(0, DistanceMeter))
        shot_info = ShotParameters(unit.Angular(0.001228, unit.AngularRadian),
                                   unit.Distance(1000, unit.DistanceYard),
                                   unit.Distance(100, unit.DistanceYard))
        wind = create_only_wind_info(unit.Velocity(5, unit.VelocityMPH),
                                     unit.Angular(-45, unit.AngularDegree))
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
        projectile = ProjectileWithDimensions(bc, unit.Distance(0.308, unit.DistanceInch),
                                              unit.Distance(1.282, unit.DistanceInch),
                                              unit.Weight(168, unit.WeightGrain))
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS))
        zero = ZeroInfo(unit.Distance(100, unit.DistanceYard))
        twist = TwistInfo(TwistRight, unit.Distance(11.24, unit.DistanceInch))
        weapon = WeaponWithTwist(unit.Distance(2, unit.DistanceInch), zero, twist)
        atmosphere = IcaoAtmosphere(Distance(0, DistanceMeter))
        shot_info = ShotParameters(unit.Angular(4.221, unit.AngularMOA),
                                   unit.Distance(1000, unit.DistanceYard),
                                   unit.Distance(100, unit.DistanceYard))
        wind = create_only_wind_info(unit.Velocity(5, unit.VelocityMPH),
                                     unit.Angular(-45, unit.AngularDegree))

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
