import math

from .drag_model import *
from .settings import Settings as Set
from .unit import *

__all__ = ('Weapon', 'Ammo', 'Projectile')


class Weapon:
    __slots__ = (
        'sight_height',
        'zero_distance',
        'twist',
        # 'click_value'
    )

    def __init__(self,
                 sight_height: [float, Distance],
                 zero_distance: [float, Distance] = Distance.Yard(100),
                 twist: [float, Distance] = Distance.Inch(0),
                 # click_value: [float, Angular] = Angular(0.25, Angular.Mil)
                 ):
        self.sight_height = sight_height if is_unit(sight_height) else Set.Units.sight_height(sight_height)
        self.zero_distance = zero_distance if is_unit(zero_distance) else Set.Units.distance(zero_distance)
        self.twist = twist if is_unit(twist) else Set.Units.twist(twist)
        # self.click_value = click_value if is_unit(click_value) else Angular(click_value, Set.Units.adjustment)


class Projectile:
    __slots__ = ('dm',
                 'weight',
                 'diameter',
                 'length')

    def __init__(self, dm: DragModel,
                 length: [float, Distance] = None):
        self.dm: DragModel = dm
        self.weight = self.dm.weight
        self.diameter = self.dm.diameter
        self.length: Distance = length if is_unit(length) else Set.Units.length(length) if length else None


class Ammo:
    __slots__ = ('projectile', 'muzzle_velocity', 'temp_modifier', 'powder_temp')

    def __init__(self, projectile: Projectile, muzzle_velocity: [float, Velocity],
                 powder_temp: [float, Temperature] = Temperature.Celsius(15),
                 temp_modifier: float = 0):
        self.projectile: Projectile = projectile
        self.muzzle_velocity: [float, Velocity] = muzzle_velocity \
            if is_unit(muzzle_velocity) else Set.Units.velocity(muzzle_velocity)
        self.temp_modifier: float = temp_modifier
        self.powder_temp: [float, Temperature] = powder_temp \
            if is_unit(powder_temp) else Set.Units.temperature(powder_temp)

    def calc_powder_sens(self, other_velocity: float | Velocity, other_temperature: [float, Temperature]):
        # (800-792) / (15 - 0) * (15/792) * 100 = 1.01
        # creates temperature modifire in percent at each 15C
        v0 = self.muzzle_velocity >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = (other_velocity if is_unit(other_velocity) else Set.Units.velocity(other_velocity)) >> Velocity.MPS
        t1 = (other_temperature if is_unit(other_temperature) else Set.Units.temperature(other_temperature)
              ) >> Temperature.Celsius

        v_delta = math.fabs(v0 - v1)
        t_delta = math.fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError("Temperature modifier error, other velocity and temperature can't be same as default")

        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100

        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp):
        temp_modifier = self.temp_modifier
        v0 = self.muzzle_velocity >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = (current_temp if is_unit(current_temp) else Set.Units.temperature(current_temp)) >> Temperature.Celsius

        t_delta = t1 - t0
        muzzle_velocity = temp_modifier / (15 / v0) * t_delta + v0

        return Velocity.MPS(muzzle_velocity)
