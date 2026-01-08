"""Example of library usage"""
import math
from dataclasses import dataclass, field

from typing import Union, NamedTuple

from py_ballisticcalc import *


class AerialTargetPrepared(NamedTuple):
    speed_fps: float
    slant_distance_ft: float
    direction_rad: float
    look_angle_rad: float
    length_ft: float


class AerialTargetPosition(NamedTuple):
    time: float
    x_shift: Angular
    y_shift: Angular
    slant_distance: Distance
    look_angle: Angular

    def __repr__(self):
        preferred = {
            "time": self.time,
            "x_shift": self.x_shift << PreferredUnits.adjustment,
            "y_shift": self.y_shift << PreferredUnits.adjustment,
            "slant_distance_ft": self.slant_distance << PreferredUnits.distance,
            "look_angle_rad": self.look_angle << PreferredUnits.angular,
        }
        fields = ', '.join(f"{k}={v!r}" for k, v in preferred.items())
        return f"AerialTargetPosition({fields})"


@dataclass
class AerialTargetMovementDirection:
    pitch: Angular
    yaw: Angular
    roll: Angular


@dataclass
class AerialTarget:
    speed: Velocity
    slant_distance: Distance
    direction_from: Angular  # AerialTargetMovementDirection.yaw
    look_angle: Angular
    length: Distance
    time_step: float

    _prepared: AerialTargetPrepared = field(repr=False)

    def __init__(self,
                 speed: Union[float, Velocity] = 0,
                 slant_distance: Union[float, Distance] = 0,
                 direction_from: Union[float, Angular] = 0,
                 look_angle: Union[float, Angular] = 0,
                 length: Union[float, Distance] = 0,
                 time_step: float = 0.1):
        self.speed = PreferredUnits.velocity(speed or 0)
        self.slant_distance = PreferredUnits.distance(slant_distance or 0)
        self.direction_from = PreferredUnits.angular(direction_from or 0)
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.length = PreferredUnits.distance(length or 0)
        self.time_step = time_step or 0.
        self._prepare()

    def _prepare(self):
        self._prepared = AerialTargetPrepared(
            self.speed >> Velocity.FPS,
            self.slant_distance >> Distance.Foot,
            self.direction_from >> Angular.Radian,
            self.look_angle >> Angular.Radian,
            self.length >> Distance.Foot,
        )

    def __repr__(self):
        preferred = {
            "speed_fps": self.speed << PreferredUnits.velocity,
            "slant_distance_ft": self.slant_distance << PreferredUnits.distance,
            "direction_from": self.direction_from << PreferredUnits.angular,
            "look_angle_rad": self.look_angle << PreferredUnits.angular,
            "length": self.length << PreferredUnits.distance,
            "time_step": self.time_step,
        }
        fields = ', '.join(f"{k}={v!r}" for k, v in preferred.items())
        return f"AerialTarget({fields})"

    def at_time(self, time_of_flight: float) -> tuple['AerialTarget', AerialTargetPosition]:
        [
            velocity_fps,
            slant_distance_ft,
            direction_angle_rad,
            look_angle_rad,
            length_ft,
        ] = self._prepared

        velocity_vector = Vector(
            math.sin(direction_angle_rad), math.cos(direction_angle_rad), 0
        ) * -velocity_fps

        distance_vector = Vector(0, math.cos(look_angle_rad), math.sin(look_angle_rad)) * slant_distance_ft

        expected_distance_vector = distance_vector + (velocity_vector * time_of_flight)

        horizontal_preemption_angle_rad = math.atan(expected_distance_vector.x / expected_distance_vector.y)
        new_look_angle_rad = math.atan(expected_distance_vector.z / expected_distance_vector.y)
        vertical_preemption_angle_rad = new_look_angle_rad - look_angle_rad
        new_slant_distance_ft = (expected_distance_vector.y / math.cos(new_look_angle_rad)) / math.cos(
            horizontal_preemption_angle_rad)

        pos = AerialTargetPosition(
            time_of_flight,
            Angular.Radian(-horizontal_preemption_angle_rad),
            Angular.Radian(-vertical_preemption_angle_rad),
            Distance.Foot(new_slant_distance_ft),
            Angular.Radian(new_look_angle_rad),
        )

        target = AerialTarget(
            self.speed,
            Distance.Foot(pos.slant_distance),
            self.direction_from,
            pos.look_angle,
            self.length,
            self.time_step
        )

        return target, pos

    def get_preemption(self, weapon: Weapon,
                       ammo: Ammo, zero_atmo: Atmo,
                       zero_distance: Distance, adjust: bool = True):

        zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
        calc = Calculator()
        calc.set_weapon_zero(zero, zero_distance)

        def get_trajectory_for_look_angle(distance: Distance, look_angle):
            shot = Shot(look_angle=look_angle,
                        weapon=weapon,
                        ammo=ammo,
                        atmo=zero_atmo)
            shot_result = calc.fire(shot, Unit.Foot((distance >> Unit.Foot) + 0.1), distance)
            return shot_result

        shot_result = get_trajectory_for_look_angle(
            Unit.Foot(self._prepared.slant_distance_ft * math.cos(self._prepared.look_angle_rad)),
            Unit.Radian(self._prepared.look_angle_rad)
        )[-1]
        _, pos = self.at_time(shot_result.time)

        if not adjust:
            logger.debug(f"t={shot_result.time:.4f}\t"
                         f"dir={self.direction_from >> Unit.Degree:.2f}\t"
                         f"sd={Unit.Foot((pos.slant_distance >> Unit.Foot) * math.cos(pos.look_angle >> Unit.Radian)) >> Unit.Meter:.2f}\t\t\t"
                         f"la={(Unit.Radian(pos.look_angle) >> Unit.Degree):.5f}\t"
                         f"xs={(pos.x_shift >> Unit.Thousandth):.5f}\t"
                         f"ys={(pos.y_shift >> Unit.Thousandth):.5f}\t"
                         f"xsd={(pos.x_shift >> Unit.Degree):.5f}\t"
                         f"ysd={(pos.y_shift >> Unit.Degree):.5f}\t")
            return pos

        initial_slant_distance_ft = self._prepared.slant_distance_ft
        initial_look_angle_rad = self._prepared.look_angle_rad
        initial_distance_ft = initial_slant_distance_ft * math.cos(initial_look_angle_rad)

        # minimal time delta to have a possibility to shoot the target
        length_delta_coeff = 1 / 5
        time_delta = self._prepared.length_ft * length_delta_coeff / self._prepared.speed_fps

        # get target movement on time step
        _, pos_delta = self.at_time(time_delta)

        new_distance_ft = (pos_delta.slant_distance >> Distance.Foot) * math.cos(pos_delta.look_angle >> Angular.Radian)
        distance_delta_ft = new_distance_ft - initial_distance_ft

        look_angle_delta_rad = -(pos_delta.y_shift >> Unit.Radian)

        # find trajectories crossing point
        prev_trajectory_match_distance_ft = 1e5
        while True:
            initial_distance_ft += distance_delta_ft
            initial_look_angle_rad += look_angle_delta_rad
            shot_result = get_trajectory_for_look_angle(
                Unit.Foot(initial_distance_ft), Unit.Radian(initial_look_angle_rad)
            )[-1]

            _, pos_adjusted = self.at_time(shot_result.time)

            cur_shot_distance_ft = shot_result.distance >> Unit.Foot
            cur_target_distance_ft = (pos_adjusted.slant_distance >> Unit.Foot) * math.cos(
                pos_adjusted.look_angle >> Unit.Radian)

            cur_trajectory_match_distance_ft = abs(cur_shot_distance_ft - cur_target_distance_ft)

            if (cur_trajectory_match_distance_ft
                    <= self._prepared.length_ft * length_delta_coeff):
                break

            if cur_trajectory_match_distance_ft >= prev_trajectory_match_distance_ft:
                break

            prev_trajectory_match_distance_ft = cur_trajectory_match_distance_ft

        logger.debug(f"t={shot_result.time:.4f}\t"
                     f"dir={self.direction_from >> Unit.Degree:.2f}\t"
                     f"sd={Unit.Foot(cur_shot_distance_ft) >> Unit.Meter:.2f}\t"
                     f"td={Unit.Foot(cur_target_distance_ft) >> Unit.Meter:.2f}\t"
                     f"la={(Unit.Radian(initial_look_angle_rad) >> Unit.Degree):.5f}\t"
                     f"xs={(pos_adjusted.x_shift >> Unit.Thousandth):.5f}\t"
                     f"ys={(pos_adjusted.y_shift >> Unit.Thousandth):.5f}\t"
                     f"xsd={(pos_adjusted.x_shift >> Unit.Degree):.5f}\t"
                     f"ysd={(pos_adjusted.y_shift >> Unit.Degree):.5f}\t"
                     f"{Unit.Foot(cur_trajectory_match_distance_ft) >> Unit.Meter:.2f}"
                     f"/{Unit.Foot(prev_trajectory_match_distance_ft) >> Unit.Meter:.2f}m")
        return pos_adjusted
