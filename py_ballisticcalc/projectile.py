from .bmath import unit
from .drag import BallisticCoefficient
from typing import Any, Union


class Projectile(object):
    _bullet_diameter: unit.Distance = None
    _bullet_length: unit.Distance = None

    """
    keeps description of a projectile
    """
    def __init__(self, ballistic_coefficient: BallisticCoefficient, weight: unit.Weight):
        """
        projectile description with dimensions
        :param ballistic_coefficient: BallisticCoefficient instance
        :param weight: unit.Weight instance
        """
        self._ballistic_coefficient = ballistic_coefficient
        self._has_dimensions = False
        self._weight = weight

    @property
    def ballistic_coefficient(self) -> BallisticCoefficient:
        """
        :return: ballistic coefficient of the projectile
        """
        return self._ballistic_coefficient

    @property
    def bullet_weight(self) -> unit.Weight:
        """
        :return: weight of the projectile
        """
        return self._weight

    @property
    def bullet_diameter(self) -> unit.Distance:
        """
        :return: the diameter (caliber) of the projectile
        """
        return self._bullet_diameter

    @property
    def bullet_length(self) -> unit.Distance:
        """
        :return: the length of the bullet
        """
        return self._bullet_length

    @property
    def has_dimensions(self) -> bool:
        """
        :return: flag indicating whether the projectile
        """
        return self._has_dimensions


class ProjectileWithDimensions(Projectile):
    """
    ProjectileWithDimensions creates the description of a projectile with dimensions (diameter and length)
    Dimensions are only required if you want to take into account projectile spin drift.
    TwistInfo must be also set in this case.
    """

    def __init__(self, ballistic_coefficient: Union[BallisticCoefficient, Any],
                 bullet_diameter: unit.Distance,
                 bullet_length: unit.Distance,
                 weight: unit.Weight):
        """
        :param ballistic_coefficient: BallisticCoefficient instance
        :param bullet_diameter: unit.Distance instance
        :param bullet_length: unit.Distance instance
        :param weight: unit.Weight instance
        """

        super(ProjectileWithDimensions, self).__init__(ballistic_coefficient, weight)
        self._has_dimensions = True
        self._bullet_diameter = bullet_diameter
        self._bullet_length = bullet_length


class Ammunition(object):
    """ Ammunition object keeps the des of ammunition (e.g. projectile loaded into a case shell) """

    def __init__(self, bullet: Projectile, muzzle_velocity: unit.Velocity):
        """
        creates the description of the ammunition
        :param bullet: Projectile instance
        :param muzzle_velocity: unit.Velocity instance
        """
        self._projectile = bullet
        self._muzzle_velocity = muzzle_velocity

    @property
    def bullet(self) -> Projectile:
        """
        :return: the description of the projectile
        """
        return self._projectile

    @property
    def muzzle_velocity(self) -> unit.Velocity:
        """
        :return: the velocity of the projectile at the muzzle
        """
        return self._muzzle_velocity
