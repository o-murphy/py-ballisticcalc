"""Module for Weapon and Ammo properties definitions"""
import math
from dataclasses import dataclass, field

from .drag_model import DragModel
from .settings import Settings as Set
from .unit import TypedUnits, Velocity, Temperature, Distance, Angular

__all__ = ('Weapon', 'Ammo')


@dataclass
class Weapon(TypedUnits):
    """
    :param sight_height: Vertical distance from center of bore line to center of sight line.
    :param twist: Distance for barrel rifling to complete one complete turn.
        Positive value => right-hand twist, negative value => left-hand twist.
    :param zero_elevation: Angle of barrel relative to sight line when sight is set to "zero."
        (Typically computed by ballistic Calculator.)
    """
    sight_height: [float, Distance] = field(default_factory=lambda: Set.Units.sight_height)
    twist: [float, Distance] = field(default_factory=lambda: Set.Units.twist)
    zero_elevation: [float, Angular] = field(default_factory=lambda: Set.Units.angular)

    def __post_init__(self):
        if not self.sight_height:
            self.sight_height = 0
        if not self.twist:
            self.twist = 0
        if not self.zero_elevation:
            self.zero_elevation = 0


@dataclass
class Ammo(TypedUnits):
    """
    :param dm: DragModel for projectile
    :param mv: Muzzle Velocity
    :param powder_temp: Baseline temperature that produces the given mv
    :param temp_modifier: Change in velocity w temperature: % per 15°C.
        Can be computed with .calc_powder_sens().  Only applies if:
            Settings.USE_POWDER_SENSITIVITY = True
    """
    dm: DragModel = field(default=None)
    mv: [float, Velocity] = field(default_factory=lambda: Set.Units.velocity)
    powder_temp: [float, Temperature] = field(default_factory=lambda: Set.Units.temperature)
    temp_modifier: float = field(default=0)

    def __post_init__(self):
        if not self.powder_temp:
            self.powder_temp = Temperature.Celsius(15)

    def calc_powder_sens(self, other_velocity: [float, Velocity],
                         other_temperature: [float, Temperature]) -> float:
        """Calculates velocity correction by temperature change; assigns to self.temp_modifier
        :param other_velocity: other velocity at other_temperature
        :param other_temperature: other temperature
        :return: temperature modifier in terms %v_delta/15°C
        """
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = Set.Units.velocity(other_velocity) >> Velocity.MPS
        t1 = Set.Units.temperature(other_temperature) >> Temperature.Celsius

        v_delta = math.fabs(v0 - v1)
        t_delta = math.fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError(
                "Temperature modifier error, other velocity"
                " and temperature can't be same as default"
            )
        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100
        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp: [float, Temperature]) -> Velocity:
        """Calculates muzzle velocity at temperature, based on temp_modifier.
        :param current_temp: Temperature of cartridge powder
        :return: Muzzle velocity corrected to current_temp
        """
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = Set.Units.temperature(current_temp) >> Temperature.Celsius
        t_delta = t1 - t0
        muzzle_velocity = self.temp_modifier / (15 / v0) * t_delta + v0
        return Velocity.MPS(muzzle_velocity)
