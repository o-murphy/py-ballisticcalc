"""Example of library usage"""
import math
from dataclasses import dataclass, field
from typing_extensions import Union, NamedTuple, Tuple
from py_ballisticcalc import *


class AerialTargetPrepared(NamedTuple):
    speed: float
    look_distance: float
    direction: float
    look_angle: float
    azimuth: float
    length: float


class AerialTargetPosition(NamedTuple):
    time: float
    x_shift: Angular
    y_shift: Angular
    look_distance: Distance
    look_angle: Angular
    azimuth: Angular

    def __repr__(self):
        preferred = {
            "time": self.time,
            "x_shift": self.x_shift << PreferredUnits.adjustment,
            "y_shift": self.y_shift << PreferredUnits.adjustment,
            "look_distance": self.look_distance << PreferredUnits.distance,
            "look_angle": self.look_angle << PreferredUnits.angular,
            "azimuth": self.look_angle << PreferredUnits.angular
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
    look_distance: Distance
    direction_from: Angular  # AerialTargetMovementDirection.yaw
    look_angle: Angular
    azimuth: Angular
    length: Distance
    time_step: float

    _prepared: AerialTargetPrepared = field(repr=False)

    def __init__(self,
                 speed: Union[float, Velocity] = 0,
                 look_distance: Union[float, Distance] = 0,
                 direction_from: Union[float, Angular] = 0,
                 look_angle: Union[float, Angular] = 0,
                 azimuth: Union[float, Angular] = 0,
                 length: Union[float, Distance] = 0,
                 time_step: float = 0.1):
        self.speed = PreferredUnits.velocity(speed or 0)
        self.look_distance = PreferredUnits.distance(look_distance or 0)
        self.direction_from = PreferredUnits.angular(direction_from or 0)
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.azimuth = PreferredUnits.angular(azimuth or 0)
        self.length = PreferredUnits.distance(length or 0)
        self.time_step = time_step or 0.
        self._prepare()

    def _prepare(self):
        self._prepared = AerialTargetPrepared(
            self.speed >> Velocity.FPS,
            self.look_distance >> Distance.Foot,
            self.direction_from >> Angular.Radian,
            self.look_angle >> Angular.Radian,
            self.azimuth >> Angular.Radian,
            self.length >> Distance.Foot,
        )

    def __repr__(self):
        preferred = {
            "speed": self.speed << PreferredUnits.velocity,
            "look_distance": self.look_distance << PreferredUnits.distance,
            "direction_from": self.direction_from << PreferredUnits.angular,
            "look_angle": self.look_angle << PreferredUnits.angular,
            "azimuth": self.azimuth << PreferredUnits.angular,
            "length": self.length << PreferredUnits.distance,
            "time_step": self.time_step,
        }
        fields = ', '.join(f"{k}={v!r}" for k, v in preferred.items())
        return f"AerialTarget({fields})"

    def at_time(self, time_of_flight: float) -> Tuple['AerialTarget', AerialTargetPosition]:
        [
            velocity_fps,
            new_look_distance_foot,
            direction_angle_rad,
            look_angle_rad,
            azimuth_rad,
            length,
        ] = self._prepared

        velocity_vector = Vector(
            math.sin(direction_angle_rad), math.cos(direction_angle_rad), 0
        ) * -velocity_fps

        distance_vector = Vector(0, math.cos(look_angle_rad), math.sin(look_angle_rad)) * new_look_distance_foot

        expected_distance_vector = distance_vector + (velocity_vector * time_of_flight)

        horizontal_preemption_angle_rad = math.atan(expected_distance_vector.x / expected_distance_vector.y)
        new_look_angle_rad = math.atan(expected_distance_vector.z / expected_distance_vector.y)
        vertical_preemption_angle_rad = new_look_angle_rad - look_angle_rad
        new_look_distance_foot = (expected_distance_vector.y / math.cos(new_look_angle_rad)) * math.cos(
            horizontal_preemption_angle_rad)
        # print(new_look_distance_foot, math.degrees(horizontal_preemption_angle_rad), math.degrees(new_look_angle_rad))
        # print(Unit.Radian(horizontal_preemption_angle_rad) >> Unit.Thousandth,
        #       Unit.Radian(vertical_preemption_angle_rad) >> Unit.Thousandth)

        # velocity_vector = Vector(
        #     x=math.sin(math.pi+direction),
        #     y=math.cos(math.pi+direction),
        #     z=0
        # ) * speed
        #
        # distance_vector = Vector(
        #     x=0,
        #     y=math.cos(look_angle),
        #     z=math.sin(look_angle)
        # ) * look_distance
        #
        # traveled_distance_vector = velocity_vector * time_of_flight
        # pos_at_time = distance_vector - traveled_distance_vector
        # # print(distance_vector, traveled_distance_vector)
        # look_angle_at_time = math.atan(pos_at_time.z / pos_at_time.y)
        # # print(pos_at_time)
        # distance = pos_at_time.z / math.sin(look_angle_at_time)
        #
        # x_shift = math.atan(pos_at_time.x / distance)
        #
        # azimuth_at_time = azimuth + x_shift
        #
        # if x_shift != 0:
        #     distance = pos_at_time.x / math.sin(x_shift)
        #
        # y_shift = look_angle - look_angle_at_time

        pos = AerialTargetPosition(
            time_of_flight,
            Angular.Radian(-horizontal_preemption_angle_rad),
            Angular.Radian(-vertical_preemption_angle_rad),
            Distance.Foot(new_look_distance_foot),
            Angular.Radian(new_look_angle_rad),
            Angular.Radian(azimuth_rad)
        )

        target = AerialTarget(
            self.speed,
            Distance.Foot(pos.look_distance),
            self.direction_from,
            pos.look_angle,
            pos.azimuth,
            self.length,
            self.time_step
        )

        return target, pos

