"""Example of library usage"""
import math
from dataclasses import dataclass, field

from typing import Optional, Union, NamedTuple

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

        # Exact 3D geometry: x - lateral, y - horizontal distance along the initial sight line, z - up
        horizontal_range_ft = math.hypot(expected_distance_vector.x, expected_distance_vector.y)
        horizontal_preemption_angle_rad = math.atan2(expected_distance_vector.x, expected_distance_vector.y)
        new_look_angle_rad = math.atan2(expected_distance_vector.z, horizontal_range_ft)
        vertical_preemption_angle_rad = new_look_angle_rad - look_angle_rad
        new_slant_distance_ft = math.hypot(horizontal_range_ft, expected_distance_vector.z)

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
                       zero_distance: Distance, adjust: bool = True,
                       calc: Optional[Calculator] = None):
        """Calculate sight adjustment (preemption) for the moving target.

        Uses `Calculator.aim()` to get the bullet time of flight to the target's
        look-distance, then moves the target for that time and repeats until the
        time of flight converges (the point where bullet and target trajectories cross).

        Args:
            weapon: Weapon (its `zero_elevation` is set from `zero_distance`).
            ammo: Ammunition.
            zero_atmo: Atmosphere at the zero and at the shot.
            zero_distance: Distance the weapon is zeroed at.
            adjust: If False, only the initial target position is used to get time of flight
                (no iteration).
            calc: Optional `Calculator` to use (default engine if omitted).
        """
        calc = calc or Calculator()
        zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
        calc.set_weapon_zero(zero, zero_distance)

        def time_of_flight(slant_distance: Distance, look_angle: Angular) -> float:
            shot = Shot(look_angle=look_angle, weapon=weapon, ammo=ammo, atmo=zero_atmo)
            _hold, _windage, point = calc.aim(shot, slant_distance)
            return point.time

        # time of flight to the target's initial position
        flight_time = time_of_flight(self.slant_distance, self.look_angle)
        _, pos = self.at_time(flight_time)

        if adjust:
            # Solve f(t) = time_of_flight(target position at t) - t = 0 with the secant method.
            # (Plain fixed-point iteration t <- time_of_flight(t) is too slow for fast targets
            # at long range, where the iteration factor approaches 1.)
            max_iterations = 30
            time_tolerance = 1e-4  # seconds

            def residual(t: float) -> float:
                _, p = self.at_time(t)
                return time_of_flight(p.slant_distance, p.look_angle) - t

            t_prev, f_prev = 0.0, flight_time  # f(0) = time of flight to the initial position
            t_cur = flight_time
            for _ in range(max_iterations):
                f_cur = residual(t_cur)
                if abs(f_cur) <= time_tolerance:
                    flight_time = t_cur + f_cur
                    break
                if f_cur == f_prev:
                    raise ArithmeticError("Preemption search stalled")
                t_prev, f_prev, t_cur = t_cur, f_cur, t_cur - f_cur * (t_cur - t_prev) / (f_cur - f_prev)
            else:
                raise ArithmeticError(
                    f"Preemption did not converge in {max_iterations} iterations (target may be unreachable)")
            _, pos = self.at_time(flight_time)

        logger.debug(f"t={flight_time:.4f}\t"
                     f"dir={self.direction_from >> Unit.Degree:.2f}\t"
                     f"sd={pos.slant_distance >> Unit.Meter:.2f}\t"
                     f"la={pos.look_angle >> Unit.Degree:.5f}\t"
                     f"xs={pos.x_shift >> Unit.Thousandth:.5f}\t"
                     f"ys={pos.y_shift >> Unit.Thousandth:.5f}\t"
                     f"xsd={pos.x_shift >> Unit.Degree:.5f}\t"
                     f"ysd={pos.y_shift >> Unit.Degree:.5f}")
        return pos
