import math
from unittest import TestCase

from aerial_targets_shooting.aerial_target import AerialTarget
from py_ballisticcalc import *

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
        delta_look = (target.look_distance >> Unit.Meter) - (pos.look_distance >> Unit.Meter)
        print(delta_look)

    def test_shot(self):
        target = AerialTarget(Velocity.MPS(200),
                              Distance.Meter(500),
                              Angular.Degree(0),
                              Angular.Degree(20),
                              Angular.Degree(0),
                              Distance.Meter(3))

        weapon = Weapon(sight_height=9.5, twist=15)
        dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
        ammo = Ammo(dm, 900)
        zero_atmo = Atmo(altitude=150, pressure=1000, temperature=15, humidity=50)
        zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
        calc = Calculator()
        calc.set_weapon_zero(zero, 500)

        def get_trajectory_for_look_angle(distance, look_angle):
            shot = Shot(look_angle=look_angle,
                        weapon=weapon,
                        ammo=ammo,
                        atmo=zero_atmo)
            shot_result = calc.fire(shot, distance + 0.1, distance)
            return shot_result

        self.assertGreater(target._prepared.look_distance,
                           target._prepared.look_distance * math.cos(target._prepared.look_angle))

        shot_result = get_trajectory_for_look_angle(
            (target.look_distance >> Unit.Meter) * math.cos(target._prepared.look_angle), target.look_angle
        )[-1]
        print('t', shot_result.time)
        _, pos = target.at_time(shot_result.time)

        # initial_look_distance = pos.look_distance >> Unit.Meter
        # initial_look_angle = pos.look_angle >> Unit.Radian
        # initial_distance = initial_look_distance * math.cos(initial_look_angle)
        initial_look_distance = target.look_distance >> Distance.Meter
        initial_look_angle = target.look_angle >> Unit.Radian
        initial_distance = initial_look_distance * math.cos(initial_look_angle)

        # minimal time delta to have a possibility to shoot the target
        length_delta_coeff = 1 / 4
        time_delta = target._prepared.length * length_delta_coeff / target._prepared.speed

        # get target movement on time step
        _, pos_delta = target.at_time(time_delta)
        distance_delta = ((
                                  pos_delta.look_distance >> Distance.Meter
                          ) - (
                                  target.look_distance >> Distance.Meter
                          )) * math.cos(pos_delta.look_angle >> Angular.Radian)
        print(distance_delta)
        self.assertLessEqual(distance_delta, 0)
        print(pos_delta.y_shift >> Unit.Degree)
        look_angle_delta = -(pos_delta.y_shift >> Unit.Radian)

        match_distance = 1e5
        while True:
            initial_distance += distance_delta
            initial_look_angle += look_angle_delta
            shot_result = get_trajectory_for_look_angle(
                initial_distance, initial_look_angle
            )[-1]

            _, pos_adjusted = target.at_time(shot_result.time)

            cur_shot_distance = shot_result.distance >> Unit.Meter
            cur_target_distance = (pos_adjusted.look_distance >> Unit.Meter) * math.cos(pos_adjusted.look_angle >> Unit.Radian)
            print(f"t={shot_result.time:.4f}\tsd={cur_shot_distance:.2f}\t"
                  f"td={cur_target_distance:.2f}\t"
                  f"la={(Unit.Radian(initial_look_angle) >> Unit.Degree):.5f}\t"
                  f"ys={(pos_adjusted.y_shift >> Unit.Degree):.5f}\t"
                  f"{cur_shot_distance - cur_target_distance}")

            if abs(cur_shot_distance - cur_target_distance) > (target.length >> Unit.Meter) * length_delta_coeff:
                if cur_shot_distance - cur_target_distance < 0:
                    raise RuntimeError("Impossible target for the ammo")
                match_distance = cur_shot_distance - cur_target_distance
                continue
            else:
                break

    def test_trajectory(self):
        for i in range(10):
            time = i/10
            direction_angle_rad = math.radians(30)
            velocity_fps = 164
            look_angle_rad = math.radians(20)
            look_distance_foot = 1640

            velocity_vector = Vector(
                math.sin(direction_angle_rad), math.cos(direction_angle_rad), 0
            ) * -velocity_fps

            distance_vector = Vector(0, math.cos(look_angle_rad), math.sin(look_angle_rad)) * look_distance_foot

            expected_distance_vector = distance_vector + (velocity_vector * time)

            horizontal_preemption_angle_rad = math.atan(expected_distance_vector.x / expected_distance_vector.y)
            new_look_angle_rad = math.atan(expected_distance_vector.z / expected_distance_vector.y)
            vertical_preemption_angle_rad = new_look_angle_rad-look_angle_rad
            look_distance_foot = (expected_distance_vector.y / math.cos(new_look_angle_rad)) * math.cos(horizontal_preemption_angle_rad)
            print(look_distance_foot, math.degrees(horizontal_preemption_angle_rad), math.degrees(new_look_angle_rad))
            print(Unit.Radian(-horizontal_preemption_angle_rad) >> Unit.Thousandth, Unit.Radian(-vertical_preemption_angle_rad) >> Unit.Thousandth)


