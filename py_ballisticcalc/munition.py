import math
from dataclasses import dataclass, field

from .drag_model import *
from .settings import Settings as Set
from .unit import *

__all__ = ('Weapon', 'Ammo', 'Projectile')


@dataclass
class Weapon(TypedUnits):
    sight_height: Set.Units.sight_height
    zero_distance: Set.Units.distance = field(default=100)
    twist: Set.Units.sight_height = field(default=0)

    def __post_init__(self):
        self.sight_height = self.sight_height


@dataclass
class Projectile(TypedUnits):
    dm: DragModel
    length: Set.Units.length = field(default=None)


@dataclass
class Ammo(TypedUnits):
    projectile: Projectile
    muzzle_velocity: Set.Units.velocity
    temp_modifier: float = 0
    powder_temp: Set.Units.temperature = field(default=Temperature.Celsius(15))

    def __post_init__(self):
        self.muzzle_velocity = self.muzzle_velocity

    def calc_powder_sens(self, other_velocity: float | Velocity,
                         other_temperature: [float, Temperature]):
        # (800-792) / (15 - 0) * (15/792) * 100 = 1.01
        # creates temperature modifire in percent at each 15C
        v0 = self.muzzle_velocity >> Velocity.MPS
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
                "Temperature modifier error, other velocity and temperature can't be same as default"
            )

        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100

        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp):
        temp_modifier = self.temp_modifier
        v0 = self.muzzle_velocity >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = (current_temp if is_unit(current_temp)
              else Set.Units.temperature(current_temp)) >> Temperature.Celsius

        t_delta = t1 - t0
        muzzle_velocity = temp_modifier / (15 / v0) * t_delta + v0

        return Velocity.MPS(muzzle_velocity)
