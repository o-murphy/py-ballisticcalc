"""Module for Weapon and Ammo properties definitions"""
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
    :param temp_modifier: Change in velocity w temperature: fps per °C.
        Can be computed with .calc_powder_sens().  Only applies if
        Settings.USE_POWDER_SENSITIVITY = True.
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
        :return: temperature modifier
        """
        v0 = self.mv >> Velocity.FPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = Set.Units.velocity(other_velocity) >> Velocity.FPS
        t1 = Set.Units.temperature(other_temperature) >> Temperature.Celsius

        if t0 == t1:
            # Can't calculate powder sensitivity without temperature differential.
            self.temp_modifier = 0.
        else:
            self.temp_modifier = (v0 - v1) / (t0 - t1)
        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp: [float, Temperature]) -> Velocity:
        """Calculates muzzle velocity at temperature, based on temp_modifier.
        :param current_temp: Temperature of cartridge.
        :return: muzzle velocity corrected to current_temp
        """
        v0 = self.mv >> Velocity.FPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = Set.Units.temperature(current_temp) >> Temperature.Celsius
        muzzle_velocity = v0 - self.temp_modifier * (t0 - t1)
        return Velocity.FPS(muzzle_velocity)
