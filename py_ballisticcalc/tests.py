import math
import timeit
import unittest
from datetime import datetime
from math import fabs

import pyximport

pyximport.install(language_level=3)

from py_ballisticcalc.profile import *
from py_ballisticcalc import unit
from py_ballisticcalc.environment import Atmosphere, Wind
from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.projectile import Projectile
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.weapon import Weapon
from py_ballisticcalc.drag_model import DragDataPoint


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
        print(data[0].drop() >> Distance.Centimeter, data[0].travelled_distance() >> Distance.Meter)
        print(data[1].drop() >> Distance.Centimeter, data[1].travelled_distance() >> Distance.Meter)
        print(data[5].drop() >> Distance.Centimeter, data[5].travelled_distance() >> Distance.Meter)
        print(data[10].drop() >> Distance.Centimeter, data[10].travelled_distance() >> Distance.Meter)
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

        p = Profile(drag_table=custom_drag_func)
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
        v = Shot(
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
        bc = DragModel(
            value=0.275,
            drag_table=TableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
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
        bc = DragModel(
            value=0.223,
            drag_table=TableG7,
            weight=Weight(167, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
        )

        ret = bc.calculated_drag_function()

    def test_mbc(self):
        bc = MultiBC(
            drag_table=TableG7,
            weight=Weight(178, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
            multiple_bc_table=[DragDataPoint(*p) for p in ((0.275, 800), (0.255, 500), (0.26, 700))],
            velocity_units_flag=Velocity.MPS
        )

        ret = bc.custom_drag_func()

    def test_create(self):
        bc = DragModel(
            value=0.223,
            drag_table=TableG7,
            weight=Weight(167, Weight.Grain),
            diameter=Distance(0.308, Distance.Inch),
        )

        p1 = Projectile(
            bc,
            Weight(167, Weight.Grain),
            Distance(0.308, Distance.Inch),
            Distance(1.2, Distance.Inch),
        )

        ammo = Ammo(p1, Velocity(800, Velocity.MPS))
        atmo = Atmosphere(Distance(0, Distance.Meter), Pressure(760, Pressure.MmHg),
                          Temperature(15, Temperature.Celsius), 0.5)

        twist = Distance(11, Distance.Inch)
        weapon = Weapon(Distance(90, Distance.Millimeter), Distance(100, Distance.Meter), twist)
        wind = [Wind()]
        calc = TrajectoryCalc()
        calc.set_max_calc_step_size(Distance(1, Distance.Foot))
        sight_angle = calc.sight_angle(ammo, weapon, atmo)
        shot_info = Shot(sight_angle, Distance(2500, Distance.Meter), Distance(1, Distance.Meter))
        return calc.trajectory(ammo, weapon, atmo, shot_info, wind)

    def test_time(self):
        t = timeit.timeit(self.test_create, number=1)
        print(datetime.fromtimestamp(t).time().strftime('%S.%fs'))


class TestPyBallisticCalc(unittest.TestCase):

    @unittest.skip
    def test_zero1(self):
        bc = DragModel(0.365, TableG1)
        projectile = Projectile(bc, unit.Weight(69, unit.Weight.Grain))
        ammo = Ammo(projectile, unit.Velocity(2600, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(3.2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        calc = TrajectoryCalc()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle >> unit.Angular.Radian - 0.001651), 1e-6,
                        f'TestZero1 failed {sight_angle >> unit.Angular.Radian:.10f}')

    @unittest.skip
    def test_zero2(self):
        bc = DragModel(0.223, TableG7)
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain))
        ammo = Ammo(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        calc = TrajectoryCalc()

        sight_angle = calc.sight_angle(ammo, weapon, atmosphere)

        self.assertLess(fabs(sight_angle >> unit.Angular.Radian - 0.001228), 1e-6,
                        f'TestZero2 failed {sight_angle >> unit.Angular.Radian:.10f}')

    def assertEqualCustom(self, a, b, accuracy, name):
        with self.subTest():
            self.assertFalse(fabs(a - b) > accuracy, f'Assertion {name} failed ({a}/{b}, {accuracy})')

    def validate_one(self, data: TrajectoryData, distance: float, velocity: float, mach: float, energy: float,
                     path: float, hold: float, windage: float, wind_adjustment: float, time: float, ogv: float,
                     adjustment_unit: Unit):

        self.assertEqualCustom(distance, data.distance >> unit.Distance.Yard, 0.001, "Distance")
        self.assertEqualCustom(velocity, data.velocity >> unit.Velocity.FPS, 5, "Velocity")
        self.assertEqualCustom(mach, data.mach, 0.005, "Mach")
        self.assertEqualCustom(energy, data.energy >> unit.Energy.FootPound, 5, "Energy")
        self.assertEqualCustom(time, data.time, 0.06, "Time")
        self.assertEqualCustom(ogv, data.ogw >> unit.Weight.Pound, 1, "OGV")

        if distance >= 800:
            self.assertEqualCustom(path, data.drop >> unit.Distance.Inch, 4, 'Drop')
        elif distance >= 500:
            self.assertEqualCustom(path, data.drop >> unit.Distance.Inch, 1, 'Drop')
        else:
            self.assertEqualCustom(path, data.drop >> unit.Distance.Inch, 0.5, 'Drop')

        if distance > 1:
            self.assertEqualCustom(hold, data.drop_adj >> adjustment_unit, 0.5, 'Hold')

        if distance >= 800:
            self.assertEqualCustom(windage, data.windage >> unit.Distance.Inch, 1.5, "Windage")
        elif distance >= 500:
            self.assertEqualCustom(windage, data.windage >> unit.Distance.Inch, 1, "Windage")
        else:
            self.assertEqualCustom(windage, data.windage >> unit.Distance.Inch, 0.5, "Windage")

        if distance > 1:
            self.assertEqualCustom(wind_adjustment, data.windage_adj >> adjustment_unit, 0.5, "WAdj")

    @unittest.skip
    def test_path_g1(self):
        bc = DragModel(0.223, TableG1)
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain))
        ammo = Ammo(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard))
        atmosphere = Atmosphere.ICAO()
        shot_info = Shot(unit.Angular(0.001228, unit.Angular.Radian),
                         unit.Distance(1000, unit.Distance.Yard),
                         unit.Distance(100, unit.Distance.Yard))
        wind = [Wind(velocity=unit.Velocity(5, unit.Velocity.MPH),
                     direction=unit.Angular(-45, unit.Angular.Degree))]
        calc = TrajectoryCalc()
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
        bc = DragModel(0.223, TableG7,
                       weight=Weight(167, Weight.Grain),
                       diameter=Distance(0.308, Distance.Inch))
        projectile = Projectile(bc, unit.Weight(168, unit.Weight.Grain),
                                unit.Distance(0.308, unit.Distance.Inch),
                                unit.Distance(1.282, unit.Distance.Inch), )
        ammo = Ammo(projectile, unit.Velocity(2750, unit.Velocity.FPS))
        twist = unit.Distance(11.24, unit.Distance.Inch)
        weapon = Weapon(unit.Distance(2, unit.Distance.Inch), unit.Distance(100, unit.Distance.Yard), twist)
        atmosphere = Atmosphere.ICAO()
        shot_info = Shot(unit.Angular(4.221, unit.Angular.MOA),
                         unit.Distance(1000, unit.Distance.Yard),
                         unit.Distance(100, unit.Distance.Yard))
        wind = [Wind(velocity=unit.Velocity(5, unit.Velocity.MPH),
                     direction=unit.Angular(-45, unit.Angular.Degree))]

        calc = TrajectoryCalc()
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


def test_back_n_forth(test, value, units):
    u = test.unit_class(value, units)
    v = u >> units
    test.assertTrue(
        math.fabs(v - value) < 1e-7
        and math.fabs(v - (u >> units) < 1e-7), f'Read back failed for {units}')


class TestAngular(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Angular
        self.unit_list = [
            Angular.Degree,
            Angular.MOA,
            Angular.MRad,
            Angular.Mil,
            Angular.Radian,
            Angular.Thousand
        ]

    def test_angular(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestDistance(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Distance
        self.unit_list = [
            Distance.Centimeter,
            Distance.Foot,
            Distance.Inch,
            Distance.Kilometer,
            Distance.Line,
            Distance.Meter,
            Distance.Millimeter,
            Distance.Mile,
            Distance.NauticalMile,
            Distance.Yard
        ]

    def test_distance(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestEnergy(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Energy
        self.unit_list = [
            Energy.FootPound,
            Energy.Joule
        ]

    def test_energy(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestPressure(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Pressure
        self.unit_list = [
            Pressure.Bar,
            Pressure.HP,
            Pressure.MmHg,
            Pressure.InHg
        ]

    def test_pressure(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Temperature
        self.unit_list = [
            Temperature.Fahrenheit,
            Temperature.Kelvin,
            Temperature.Celsius,
            Temperature.Rankin
        ]

    def test_temperature(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Velocity
        self.unit_list = [
            Velocity.FPS,
            Velocity.KMH,
            Velocity.KT,
            Velocity.MPH,
            Velocity.MPS
        ]

    def test_velocity(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestWeight(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_class = Weight
        self.unit_list = [
            Weight.Grain,
            Weight.Gram,
            Weight.Kilogram,
            Weight.Newton,
            Weight.Ounce,
            Weight.Pound
        ]

    def test_weight(self):
        for u in self.unit_list:
            with self.subTest(unit=u):
                test_back_n_forth(self, 3, u)


class TestUnitConversionSyntax(unittest.TestCase):

    def setUp(self) -> None:
        self.low = Distance(10, Distance.Yard)
        self.high = Distance(100, Distance.Yard)

    def test__eq__(self):
        self.assertEqual(self.low, 360)
        self.assertEqual(360, self.low)
        self.assertEqual(self.low, self.low)
        self.assertEqual(self.low, Distance(30, Distance.Foot))

    def test__ne__(self):
        self.assertNotEqual(Distance(100, Distance.Yard), Distance(90, Distance.Yard))

    def test__lt__(self):
        self.assertLess(self.low, self.high)
        self.assertLess(10, self.high)
        self.assertLess(self.low, 9999)

    def test__gt__(self):
        self.assertGreater(self.high, self.low)
        self.assertGreater(self.high, 10)
        self.assertGreater(9000, self.low)

    def test__ge__(self):
        self.assertGreaterEqual(self.high, self.low)
        self.assertGreaterEqual(self.high, self.high)

        self.assertGreaterEqual(self.high, 90)
        self.assertGreaterEqual(self.high, 0)

    def test__le__(self):
        self.assertLessEqual(self.low, self.high)
        self.assertLessEqual(self.high, self.high)

        self.assertLessEqual(self.low, 360)
        self.assertLessEqual(self.low, 360)

    def test__rshift__(self):
        self.assertIsInstance(self.low >> Distance.Meter, (int, float))
        self.low >>= Distance.Meter
        self.assertIsInstance(self.low, (int, float))

    def test__lshift__(self):
        desired_unit_type = Distance
        desired_units = Distance.Foot
        converted = self.low << desired_units
        self.assertIsInstance(converted, desired_unit_type)
        self.assertEqual(converted.units, desired_units)
        self.low <<= desired_units
        self.assertEqual(self.low.units, desired_units)

    @unittest.skip
    def test__getattribute__(self):
        converted = self.low.Foot
        self.assertIsInstance(converted, Distance)
        self.assertEqual(converted.units, Distance.Foot)


if __name__ == '__main__':
    unittest.main()
