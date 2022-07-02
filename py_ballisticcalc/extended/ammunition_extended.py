from ..weapon import Ammunition
from .projectile_extended import ProjectileExtended
from ..bmath import unit


class AmmunitionExtended(Ammunition):

    def __init__(self, bullet: ProjectileExtended, muzzle_velocity: unit.Velocity):
        """
        creates the description of the ammunition
        :param bullet: Projectile instance
        :param muzzle_velocity: unit.Velocity instance
        """
        super().__init__(bullet, muzzle_velocity)
        self._projectile = bullet
        self._muzzle_velocity = muzzle_velocity

    @property
    def bullet(self) -> ProjectileExtended:
        """
        :return: the description of the projectile
        """
        return self._projectile
