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


@dataclass
class Ammo:
    projectile: Projectile
    muzzle_velocity: Velocity
