"""Module for Weapon and Ammo properties definitions"""
import math
from dataclasses import dataclass, field

from .settings import Settings as Set
from .unit import TypedUnits, Velocity, Temperature, Distance, Angular

__all__ = ('Weapon', 'Ammo')


@dataclass
class Weapon(TypedUnits):
    """
    :param zero_distance: Sight-line distance to "zero," which is point we want to hit.
        This is the distance that a rangefinder would return with no ballistic adjustment.
        NB: Some rangefinders offer an adjusted distance based on inclinometer measurement.
            However, without a complete ballistic model these can only approximate the effects
            on ballistic trajectory of shooting uphill or downhill.  Therefore:
            For maximum accuracy, use the raw sight distance and look angle as inputs here.
    :param zero_look_angle: If = 0 then the target zero is horizontal with the gun at zero_distance.
        If zero_look_angle != 0 then the target zero is at a different height than the gun, and
            the horizontal distance to target = cos(look_angle) * zero_distance, and
            the vertical distance to target from horizontal = sin(look_angle) * zero_distance.
    """
    sight_height: [float, Distance] = field(default_factory=lambda: Set.Units.sight_height)
    zero_distance: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    twist: [float, Distance] = field(default_factory=lambda: Set.Units.twist)
    zero_look_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)

    def __post_init__(self):
        if not self.twist:
            self.twist = 0
        if not self.zero_look_angle:
            self.zero_look_angle = 0


@dataclass
class Ammo(TypedUnits):
    """Creates Ammo and Projectile properties"""

    dm: 'DragModel'
    length: [float, Distance] = field(default_factory=lambda: Set.Units.length)
    mv: [float, Velocity] = field(default_factory=lambda: Set.Units.velocity)
    temp_modifier: float = field(default=0)
    powder_temp: [float, Temperature] = field(default_factory=lambda: Temperature.Celsius(15))

    def calc_powder_sens(self, other_velocity: [float, Velocity],
                         other_temperature: [float, Temperature]) -> float:
        """Calculates velocity correction by temperature change
        :param other_velocity: other velocity
        :param other_temperature: other temperature
        :return: temperature modifier
        """
        # (800-792) / (15 - 0) * (15/792) * 100 = 1.01
        # creates temperature modifier in percent at each 15C
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = Set.Units.velocity(other_velocity) >> Velocity.MPS
        t1 = Set.Units.temperature(other_temperature) >> Temperature.Celsius

        v_delta = math.fabs(v0 - v1)
        t_delta = math.fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError(
                "Temperature modifier error, other velocity "
                "and temperature can't be same as default"
            )

        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100

        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp: [float, Temperature]) -> Velocity:
        """Calculates current velocity by temperature correction
        :param current_temp: temperature on current atmosphere
        :return: velocity corrected for temperature specified
        """
        temp_modifier = self.temp_modifier
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = Set.Units.temperature(current_temp) >> Temperature.Celsius

        t_delta = t1 - t0
        muzzle_velocity = temp_modifier / (15 / v0) * t_delta + v0

        return Velocity.MPS(muzzle_velocity)
