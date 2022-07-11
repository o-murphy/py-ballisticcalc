from py_ballisticcalc.lib.bmath.unit import *
from py_ballisticcalc.lib.drag import *


cdef class Projectile:
    cdef _bullet_diameter
    cdef _bullet_length
    cdef _ballistic_coefficient
    cdef _has_dimensions
    cdef _weight

    def __init__(self, ballistic_coefficient: BallisticCoefficient, weight: Weight):
        """
        projectile description with dimensions
        :param ballistic_coefficient: BallisticCoefficient instance
        :param weight: unit.Weight instance
        """
        self._ballistic_coefficient = ballistic_coefficient
        self._has_dimensions = False
        self._weight = weight

    cpdef ballistic_coefficient(self):
        return self._ballistic_coefficient

    cpdef bullet_weight(self):
        return self._weight

    cpdef bullet_diameter(self):
        return self._bullet_diameter

    cpdef bullet_length(self):
        return self._bullet_length

    cpdef has_dimensions(self):
        return self._has_dimensions


cdef class ProjectileWithDimensions(Projectile):

    def __init__(self, ballistic_coefficient: BallisticCoefficient,
                 bullet_diameter: Distance,
                 bullet_length: Distance,
                 weight: Weight):
        super(ProjectileWithDimensions, self).__init__(ballistic_coefficient, weight)
        self._has_dimensions = True
        self._bullet_diameter = bullet_diameter
        self._bullet_length = bullet_length

cdef class Ammunition:
    cdef _projectile
    cdef _muzzle_velocity

    def __init__(self, bullet: Projectile, muzzle_velocity: Velocity):
        self._projectile = bullet
        self._muzzle_velocity = muzzle_velocity

    cpdef bullet(self):
        return self._projectile

    cpdef muzzle_velocity(self):
        return self._muzzle_velocity
