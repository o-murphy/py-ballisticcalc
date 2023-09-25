from dataclasses import dataclass

from .drag_model import *
from .unit import *

__all__ = ('Ammo', 'Projectile')


@dataclass
class Projectile:
    dm: DragModel
    weight: Weight
    diameter: Distance = None
    length: Distance = None

    def __init__(self, dm: DragModel,
                 weight: [float, Weight],
                 diameter: [float, Distance] = None,
                 length: [float, Distance] = None):

        self.dm = dm
        self.weight = weight if is_unit(weight) else Weight(weight, DefaultUnits.weight)
        self.diameter = diameter if is_unit(diameter) else Distance(diameter, DefaultUnits.diameter) if diameter else None
        self.length = length if is_unit(length) else Distance(length, DefaultUnits.length) if length else None


@dataclass
class Ammo:
    __slots__ = ('projectile', 'muzzle_velocity')

    projectile: Projectile
    muzzle_velocity: Velocity

    def __init__(self, projectile: Projectile, muzzle_velocity: [float, Velocity]):

        self.projectile = projectile
        self.muzzle_velocity = muzzle_velocity if is_unit(muzzle_velocity) else \
            Velocity(muzzle_velocity, DefaultUnits.velocity)
