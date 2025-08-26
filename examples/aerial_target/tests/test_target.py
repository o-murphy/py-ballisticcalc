import logging
import math
from unittest import TestCase

from aerial_targets_shooting.aerial_target import AerialTarget
from py_ballisticcalc import *

logger.setLevel(logging.DEBUG)

PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Thousandth
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter
PreferredUnits.angular = Angular.Degree
PreferredUnits.pressure = Pressure.hPa


class TestTarget(TestCase):

    def test_direction(self):

        target = AerialTarget(Velocity.MPS(50),
                              Distance.Meter(1000),
                              Angular.Degree(45),
                              Angular.Degree(20),
                              Angular.Degree(0),
                              Distance.Meter(3))

        for dir in range(0, 90, 15):
            with self.subTest():
                target.direction_from = Angular.Degree(dir)
                target._prepare()
                _, pos = target.at_time(1)
                self.assertGreaterEqual((pos.x_shift >> Unit.Degree), 0)
                self.assertLessEqual((pos.y_shift >> Unit.Degree), 0)

                self.assert_deltas(target, pos)

        for dir in range(90, 181, 15):
            with self.subTest():
                target.direction_from = Angular.Degree(dir)
                target._prepare()
                _, pos = target.at_time(1)
                self.assertGreaterEqual((pos.x_shift >> Unit.Degree), 0)
                self.assertGreaterEqual((pos.y_shift >> Unit.Degree), 0)

                self.assert_deltas(target, pos)

        for dir in range(-90, -181, -15):
            with self.subTest():
                target.direction_from = Angular.Degree(dir)
                target._prepare()
                _, pos = target.at_time(1)
                self.assertLessEqual((pos.x_shift >> Unit.Degree), 0)
                self.assertGreaterEqual((pos.y_shift >> Unit.Degree), 0)

                self.assert_deltas(target, pos)

        for dir in range(0, -90, -15):
            with self.subTest():
                target.direction_from = Angular.Degree(dir)
                target._prepare()
                _, pos = target.at_time(1)
                self.assertLessEqual((pos.x_shift >> Unit.Degree), 0)
                self.assertLessEqual((pos.y_shift >> Unit.Degree), 0)

                self.assert_deltas(target, pos)

    def assert_deltas(self, target, pos):
        delta_look = (target.slant_distance_ft >> Unit.Meter) - (pos.slant_distance_ft >> Unit.Meter)
        print(delta_look)

    def test_shot(self):
        target = AerialTarget(Velocity.MPS(50),
                              Distance.Meter(500),
                              Angular.Degree(0),
                              Angular.Degree(20),
                              Angular.Degree(0),
                              Distance.Meter(3))

        weapon = Weapon(sight_height=9.5, twist=15)
        dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
        ammo = Ammo(dm, 900)
        zero_atmo = Atmo(altitude=150, pressure=1000, temperature=15, humidity=50)

        target.get_preemption(weapon, ammo, zero_atmo, Distance.Meter(500))

    def test_trajectory(self):
        for i in range(10):
            time = i / 10
            direction_angle_rad = math.radians(30)
            velocity_fps = 164
            look_angle_rad = math.radians(20)
            slant_distance_foot = 1640

            velocity_vector = Vector(
                math.sin(direction_angle_rad), math.cos(direction_angle_rad), 0
            ) * -velocity_fps

            distance_vector = Vector(0, math.cos(look_angle_rad), math.sin(look_angle_rad)) * slant_distance_foot

            expected_distance_vector = distance_vector + (velocity_vector * time)

            horizontal_preemption_angle_rad = math.atan(expected_distance_vector.x / expected_distance_vector.y)
            new_look_angle_rad = math.atan(expected_distance_vector.z / expected_distance_vector.y)
            vertical_preemption_angle_rad = new_look_angle_rad - look_angle_rad
            slant_distance_foot = (expected_distance_vector.y / math.cos(new_look_angle_rad)) * math.cos(
                horizontal_preemption_angle_rad)
            print(slant_distance_foot, math.degrees(horizontal_preemption_angle_rad), math.degrees(new_look_angle_rad))
            print(Unit.Radian(-horizontal_preemption_angle_rad) >> Unit.Thousandth,
                  Unit.Radian(-vertical_preemption_angle_rad) >> Unit.Thousandth)
