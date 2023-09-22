import timeit
import unittest
from datetime import datetime
from math import fabs

import pyximport

from py_ballisticcalc.drag_tables import DragDataPoint

pyximport.install(language_level=3)

from py_ballisticcalc.profile import *
from py_ballisticcalc import unit
from py_ballisticcalc.atmosphere import Atmosphere
from py_ballisticcalc.drag import DragTableG1
from py_ballisticcalc.projectile import Projectile
from py_ballisticcalc.shot_parameters import ShotParameters
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.weapon import Weapon


class TestProfile(unittest.TestCase):
    """
    0.22300000488758087
    -9.000000953674316 0.0
    -0.00047645941958762705 100.0496826171875
    -188.0503692626953 500.03924560546875
    -1475.96826171875 1000.0016479492188
    1.5700003132224083e-05 def init
    0.09897580003598705 def init + make
    0.2844648000318557 max=2500m, step=1m
    0.04717749997507781 max=2500m, step=1m, max_step=5ft
    """

    @unittest.skip
    def test_profile_bc(self):
        p = Profile()
        data = p.calculate_trajectory()
        print(data[0].drop().get_in(Distance.Centimeter), data[0].travelled_distance().get_in(Distance.Meter))
        print(data[1].drop().get_in(Distance.Centimeter), data[1].travelled_distance().get_in(Distance.Meter))
        print(data[5].drop().get_in(Distance.Centimeter), data[5].travelled_distance().get_in(Distance.Meter))
        print(data[10].drop().get_in(Distance.Centimeter), data[10].travelled_distance().get_in(Distance.Meter))
        p.calculate_drag_table()
        print(p.dict())

    def test_custom_df(self):
        custom_drag_func = [
            {'Mach': 0.0, 'CD': 0.18}, {'Mach': 0.4, 'CD': 0.178}, {'Mach': 0.5, 'CD': 0.154},
            {'Mach': 0.6, 'CD': 0.129}, {'Mach': 0.7, 'CD': 0.131}, {'Mach': 0.8, 'CD': 0.136},
            {'Mach': 0.825, 'CD': 0.14}, {'Mach': 0.85, 'CD': 0.144}, {'Mach': 0.875, 'CD': 0.153},
            {'Mach': 0.9, 'CD': 0.177}, {'Mach': 0.925, 'CD': 0.226}, {'Mach': 0.95, 'CD': 0.26},
            {'Mach': 0.975, 'CD': 0.349}, {'Mach': 1.0, 'CD': 0.427}, {'Mach': 1.025, 'CD': 0.45},
            {'Mach': 1.05, 'CD': 0.452}, {'Mach': 1.075, 'CD': 0.45}, {'Mach': 1.1, 'CD': 0.447},
            {'Mach': 1.15, 'CD': 0.437}, {'Mach': 1.2, 'CD': 0.429}, {'Mach': 1.3, 'CD': 0.418},
            {'Mach': 1.4, 'CD': 0.406}, {'Mach': 1.5, 'CD': 0.394}, {'Mach': 1.6, 'CD': 0.382},
            {'Mach': 1.8, 'CD': 0.359}, {'Mach': 2.0, 'CD': 0.339}, {'Mach': 2.2, 'CD': 0.321},
            {'Mach': 2.4, 'CD': 0.301}, {'Mach': 2.6, 'CD': 0.28}, {'Mach': 3.0, 'CD': 0.25},
            {'Mach': 4.0, 'CD': 0.2}, {'Mach': 5.0, 'CD': 0.18}
        ]

        p = Profile(drag_table=0, custom_drag_function=custom_drag_func)
        data = p.calculate_trajectory()

    def test_time(self):
        with self.subTest('def init') as st:
            print(timeit.timeit(lambda: Profile(), number=1), 'def init')

        with self.subTest('def init + make'):
            p = Profile()
            print(timeit.timeit(lambda: p.calculate_trajectory(), number=1), 'def init + make', )

        with self.subTest('max=2500m, step=1m'):
            p = Profile(
                maximum_distance=(2500, unit.Distance.Meter),
                distance_step=(1, unit.Distance.Meter),
            )
            print(timeit.timeit(lambda: p.calculate_trajectory(), number=1), 'max=2500m, step=1m')

        with self.subTest('max=2500m, step=1m, max_step=5ft'):
            p = Profile(
                maximum_distance=(2500, unit.Distance.Meter),
                distance_step=(1, unit.Distance.Meter),
                maximum_step_size=(5, unit.Distance.Foot)
            )
            print(timeit.timeit(lambda: p.calculate_trajectory(), number=1), 'max=2500m, step=1m, max_step=5ft')

        with self.subTest('custom_df'):
            print(timeit.timeit(self.test_custom_df, number=1), 'max=2500m, step=1m, max_step=5ft, custom_df')


class TestAtmo(unittest.TestCase):

    def test_create(self):
        v = Atmosphere(
            altitude=Distance(0, Distance.Meter),
            pressure=Pressure(760, Pressure.MmHg),
            temperature=Temperature(15, Temperature.Celsius),
            humidity=0.5
        )

        icao = Atmosphere.ICAO()

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(t)


class TestShotParams(unittest.TestCase):

    def test_create(self):
        v = ShotParameters(
            Angular(0, Angular.Degree),
            Distance(1000, Distance.Foot),
            Distance(100, Distance.Foot)
        )

    # @unittest.SkipTest
    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))


class TestDrag(unittest.TestCase):

    def setUp(self) -> None:
        self.bc = self.test_create()

    def test_create(self):
        bc = BallisticCoefficient(
            value=0.275,
            drag_table=DragTableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            custom_drag_table=[]
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
            drag_table=DragTableG7,
            weight=Weight(167, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            custom_drag_table=[]
        )

        print(bc.form_factor())
        print(bc.drag(3))

        ret = bc.calculated_drag_function()
        # print(ret)

    def test_mbc(self):
        bc = MultipleBallisticCoefficient(
            drag_table=DragTableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            multiple_bc_table=[DragDataPoint(*p) for p in ((0.275, 800), (0.255, 500), (0.26, 700))],
            velocity_units_flag=Velocity.MPS
        )

        ret = bc.custom_drag_func()

    def test_create(self):
        bc = BallisticCoefficient(
            value=0.223,
            drag_table=DragTableG7,
            weight=Weight(167, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            custom_drag_table=[]
        )

        p1 = Projectile(
            bc,
            Weight(167, Weight.Grain),
            Distance(0.308, Distance.Inch),
            Distance(1.2, Distance.Inch),
        )

        ammo = Ammunition(p1, Velocity(800, Velocity.MPS))
        atmo = Atmosphere(Distance(0, Distance.Meter), Pressure(760, Pressure.MmHg),
                          Temperature(15, Temperature.Celsius), 0.5)

        twist = Distance(11, Distance.Inch)
        weapon = Weapon(Distance(90, Distance.Millimeter), Distance(100, Distance.Meter), twist)
        wind = [WindInfo()]
        calc = TrajectoryCalculator()
        calc.set_maximum_calculator_step_size(Distance(1, Distance.Foot))
        print(timeit.timeit(lambda: calc.sight_angle(ammo, weapon, atmo), number=1))
        sight_angle = calc.sight_angle(ammo, weapon, atmo)
        shot_info = ShotParameters(sight_angle, Distance(2500, Distance.Meter), Distance(1, Distance.Meter))
        return calc.trajectory(ammo, weapon, atmo, shot_info, wind)

    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))


class TestPyBallisticCalc(unittest.TestCase):

    @unittest.skip
    def test_zero1(self):
        bc = BallisticCoefficient(0.365, DragTableG1)
        projectile = Projectile(bc, unit.Weight(69, unit.Weight.Grain))
        ammo = Ammunition(projectile, unit.Velocity(2600, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(3.2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle.get_in(unit.Angular.Radian) - 0.001651), 1e-6,
                        f'TestZero1 failed {sight_angle.get_in(unit.Angular.Radian):.10f}')

    @unittest.skip
    def test_zero2(self):
        bc = BallisticCoefficient(0.223, DragTableG7)
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain))
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        calc = TrajectoryCalculator()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle.get_in(unit.Angular.Radian) - 0.001228), 1e-6,
                        f'TestZero2 failed {sight_angle.get_in(unit.Angular.Radian):.10f}')

    def assertEqualCustom(self, a, b, accuracy, name):
        with self.subTest():
            self.assertFalse(fabs(a - b) > accuracy, f'Assertion {name} failed ({a}/{b}, {accuracy})')

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float, mach: float, energy: float,
                     path: float, hold: float, windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: Unit):

        self.assertEqualCustom(distance, data.distance.get_in(unit.Distance.Yard), 0.001, "Distance")
        self.assertEqualCustom(velocity, data.velocity.get_in(unit.Velocity.FPS), 5, "Velocity")
        self.assertEqualCustom(mach, data.mach, 0.005, "Mach")
        self.assertEqualCustom(energy, data.energy.get_in(unit.Energy.FootPound), 5, "Energy")
        self.assertEqualCustom(time, data.time, 0.06, "Time")
        self.assertEqualCustom(ogv, data.ogw.get_in(unit.Weight.Pound), 1, "OGV")

        if distance >= 800:
            self.assertEqualCustom(path, data.drop.get_in(unit.Distance.Inch), 4, 'Drop')
        elif distance >= 500:
            self.assertEqualCustom(path, data.drop.get_in(unit.Distance.Inch), 1, 'Drop')
        else:
            self.assertEqualCustom(path, data.drop.get_in(unit.Distance.Inch), 0.5, 'Drop')

        if distance > 1:
            self.assertEqualCustom(hold, data.drop_adjustment.get_in(adjustment_unit), 0.5, 'Hold')

        if distance >= 800:
            self.assertEqualCustom(windage, data.windage.get_in(unit.Distance.Inch), 1.5, "Windage")
        elif distance >= 500:
            self.assertEqualCustom(windage, data.windage.get_in(unit.Distance.Inch), 1, "Windage")
        else:
            self.assertEqualCustom(windage, data.windage.get_in(unit.Distance.Inch), 0.5, "Windage")

        if distance > 1:
            self.assertEqualCustom(wind_adjustment, data.windage_adjustment.get_in(adjustment_unit), 0.5, "WAdj")

    @unittest.skip
    def test_path_g1(self):
        bc = BallisticCoefficient(0.223, DragTableG1)
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain))
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        shot_info = ShotParameters(unit.Angular(0.001228, unit.Angular.Radian),
                                   unit.Distance(1000, unit.Distance.Yard),
                                   unit.Distance(100, unit.Distance.Yard))
        wind = [WindInfo(velocity=unit.Velocity(5, unit.Velocity.MPH),
                         direction=unit.Angular(-45, unit.Angular.Degree))]
        calc = TrajectoryCalculator()
        data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

        self.assertEqualCustom(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.Angular.MOA],
            [data[1], 100, 2351.2, 2.106, 2061, 0, 0, -0.6, -0.6, 0.118, 550, unit.Angular.MOA],
            [data[5], 500, 1169.1, 1.047, 509.8, -87.9, -16.8, -19.5, -3.7, 0.857, 67, unit.Angular.MOA],
            [data[10], 1000, 776.4, 0.695, 224.9, -823.9, -78.7, -87.5, -8.4, 2.495, 20, unit.Angular.MOA]
        ]

        for d in test_data:
            with self.subTest():
                self.validate_one(*d)

    def test_path_g7(self):
        bc = BallisticCoefficient(0.223, DragTableG7,
                                  weight=Weight(167, Weight.Grain),
                                  diameter=Distance(0.308, Distance.Inch),
                                  custom_drag_table=[])
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain),
                                unit.Distance(0.308, unit.Distance.Inch),
                                unit.Distance(1.282, unit.Distance.Inch), )
        ammo = Ammunition(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        twist = unit.Distance(11.24, unit.Distance.Inch)
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard), twist)
        atmosphere = Atmosphere.ICAO()
        shot_info = ShotParameters(unit.Angular(4.221, unit.Angular.MOA),
                                   unit.Distance(1000, unit.Distance.Yard),
                                   unit.Distance(100, unit.Distance.Yard))
        wind = [WindInfo(velocity=unit.Velocity(5, unit.Velocity.MPH),
                         direction=unit.Angular(-45, unit.Angular.Degree))]

        calc = TrajectoryCalculator()
        data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

        self.assertEqualCustom(len(data), 11, 0.1, "Length")

        test_data = [
            [data[0], 0, 2750, 2.463, 2820.6, -2, 0, 0, 0, 0, 880, unit.Angular.Mil],
            [data[1], 100, 2544.3, 2.279, 2416, 0, 0, -0.35, -0.09, 0.113, 698, unit.Angular.Mil],
            [data[5], 500, 1810.7, 1.622, 1226, -56.3, -3.18, -9.96, -0.55, 0.673, 252, unit.Angular.Mil],
            [data[10], 1000, 1081.3, 0.968, 442, -401.6, -11.32, -50.98, -1.44, 1.748, 55, unit.Angular.Mil]
        ]

        for d in test_data:
            with self.subTest():
                self.validate_one(*d)
