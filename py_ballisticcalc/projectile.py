from dataclasses import dataclass

from .drag import *
from .bmath.unit import *


@dataclass
class Projectile:
    bc: BallisticCoefficient
    weight: Weight
    diameter: Distance = None
    length: Distance = None


@dataclass
class Ammunition:
    projectile: Projectile
    muzzle_velocity: Velocity
