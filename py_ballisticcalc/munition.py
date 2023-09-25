from .settings import DefaultUnits
from .drag_model import *
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
                 zero_distance: [float, Distance] = Distance(100, Distance.Yard),
                 twist: [float, Distance] = Distance(0, Distance.Inch),
                 # click_value: [float, Angular] = Angular(0.25, Angular.Mil)
                 ):
        self.sight_height = sight_height if is_unit(sight_height) else Distance(sight_height, DefaultUnits.sight_height)
        self.zero_distance = zero_distance if is_unit(zero_distance) else Distance(zero_distance, DefaultUnits.distance)
        self.twist = twist if is_unit(twist) else Distance(twist, DefaultUnits.twist)
        # self.click_value = click_value if is_unit(click_value) else Angular(click_value, DefaultUnits.adjustment)


class Projectile:
    __slots__ = ('dm',
                 'weight',
                 'diameter',
                 'length')

    def __init__(self, dm: DragModel,
                 # weight: [float, Weight],
                 # diameter: [float, Distance] = None,
                 length: [float, Distance] = None):
        self.dm: DragModel = dm
        self.weight = self.dm.weight()
        self.diameter = self.dm.diameter()
        # self.weight: Weight = weight if is_unit(weight) else Weight(weight, DefaultUnits.weight)
        # self.diameter: Distance = diameter if is_unit(diameter) else Distance(
        #     diameter, DefaultUnits.diameter) if diameter else None
        self.length: Distance = length if is_unit(length) else Distance(
            length, DefaultUnits.length) if length else None


class Ammo:
    __slots__ = ('projectile', 'muzzle_velocity', 'powder_sens', 'powder_temp')

    def __init__(self, projectile: Projectile, muzzle_velocity: [float, Velocity],
                 powder_sens: float = 1, powder_temp: [float, Temperature] = Temperature(15, Temperature.Celsius)):
        self.projectile: Projectile = projectile
        self.muzzle_velocity: Velocity = muzzle_velocity if is_unit(muzzle_velocity) else Velocity(
            muzzle_velocity, DefaultUnits.velocity)
        self.powder_sens: float = powder_sens
        self.powder_temp: [float, Temperature] = powder_temp

    def _calc_powder_sens(self, v1, t1):
        v0 = self.muzzle_velocity >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        temp_difference = t0 - t1
        speed_difference = v0 - v1
        temp_modifier = (speed_difference / temp_difference) * (15 / v0) * 100
        self.powder_sens = temp_modifier
        return self.powder_sens

    def _get_velocity_for_temp(self, t):
        powder_temp = (self.powder_temp >> Temperature.Celsius) / 100
        mv = self.muzzle_velocity >> Velocity.MPS
        temp_difference = powder_temp - t
        current_velocity = mv - self.powder_sens / (15 * mv * temp_difference)
        return current_velocity

