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
            speed,
            look_distance,
            direction,
            look_angle,
            azimuth,
            length,
        ] = self._prepared

        direction_vector = Vector(
            x=math.sin(direction),
            y=math.cos(direction),
            z=0
        )

        length_vector = direction_vector * length  # FIXME: not using now
        velocity_vector = direction_vector * speed

        distance_vector = Vector(
            x=0,
            y=math.cos(look_angle) * look_distance,
            z=math.sin(look_angle) * look_distance
        )

        traveled_distance_vector = velocity_vector * time_of_flight
        pos_at_time = distance_vector + length_vector - traveled_distance_vector
        # print(distance_vector, traveled_distance_vector)
        look_angle_at_time = math.atan(pos_at_time.z / pos_at_time.y)
        # print(pos_at_time)
        distance = pos_at_time.z / math.sin(look_angle_at_time)

        x_shift = math.atan(pos_at_time.x / distance)

        azimuth_at_time = azimuth + x_shift

        if x_shift != 0:
            distance = pos_at_time.x / math.sin(x_shift)

        y_shift = look_angle - look_angle_at_time

        pos = AerialTargetPosition(
            time_of_flight,
            Angular.Radian(x_shift),
            Angular.Radian(y_shift),
            Distance.Foot(distance),
            Angular.Radian(look_angle_at_time),
            Angular.Radian(azimuth_at_time)
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

