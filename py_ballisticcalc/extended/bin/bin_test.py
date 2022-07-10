import timeit
from datetime import datetime
import unittest
import pyximport
pyximport.install()
from py_ballisticcalc.extended.bin.atmosphere import *
from py_ballisticcalc.extended.bin.projectile import *
from py_ballisticcalc.extended.bin.weapon import *
from py_ballisticcalc.extended.bin.wind import *
from py_ballisticcalc.extended.bin.shot_parameters import *
from py_ballisticcalc.extended.bin.trajectory_calculator import *


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
        v = ShotParameterUnlevel(
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
    def test_create(self):
        bc = BallisticCoefficient(
            value=0.223,
            drag_table=DragTableG7
        )

        # p0 = Projectile(
        #     bc, Weight(178, WeightGrain)
        # )

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
        # sight_angle = calc.sight_angle(ammo, weapon, atmo)
        # print(sight_angle)
        sight_angle = Angular(0, AngularDegree)
        shot_info = ShotParameters(sight_angle, Distance(2500, DistanceMeter), Distance(100, DistanceMeter))
        return calc.trajectory(ammo, weapon, atmo, shot_info, wind)

    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))

        data = self.test_create()
        print(data)
        for i, d in enumerate(data):
            distance = d.travelled_distance().convert(DistanceMeter)
            g7_path = d.drop().convert(DistanceCentimeter)
            # custom_path = custom_drag_func_trajectory[i].drop.convert(DistanceCentimeter)
            print(f'Distance: {distance}, i7 * G7 BC: {g7_path}')
