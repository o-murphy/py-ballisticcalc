"""Module for Weapon and Ammo properties definitions"""

import math
from dataclasses import dataclass, field

# pylint: disable=import-error,no-name-in-module
from .drag_model import DragModel
from .settings import Settings as Set
from .unit import TypedUnits, Velocity, Temperature, is_unit, Distance

__all__ = ('Weapon', 'Ammo')


@dataclass
class Weapon(TypedUnits):
    """Creates Weapon properties"""
    sight_height: [float, Distance] = field(default_factory=lambda: Set.Units.sight_height)
    zero_distance: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    twist: [float, Distance] = field(default_factory=lambda: Set.Units.twist)

    def __post_init__(self):
        if not self.twist:
            self.twist = 0


@dataclass
class Ammo(TypedUnits):
    """Creates Ammo and Projectile properties"""

    dm: DragModel
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
        v1 = (other_velocity if is_unit(other_velocity)
              else Set.Units.velocity(other_velocity)) >> Velocity.MPS
        t1 = (other_temperature if is_unit(other_temperature)
              else Set.Units.temperature(other_temperature)) >> Temperature.Celsius

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
        t1 = (current_temp if is_unit(current_temp)
              else Set.Units.temperature(current_temp)) >> Temperature.Celsius

        t_delta = t1 - t0
        muzzle_velocity = temp_modifier / (15 / v0) * t_delta + v0

        return Velocity.MPS(muzzle_velocity)
