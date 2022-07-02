from ..projectile import Projectile, ProjectileWithDimensions
from .drag_extended import BallisticCoefficientExtended
from ..bmath import unit


class ProjectileExtended(Projectile):
    def __init__(self, ballistic_coefficient: BallisticCoefficientExtended, weight: unit.Weight):
        super(ProjectileExtended, self).__init__(ballistic_coefficient, weight)
        self._ballistic_coefficient = ballistic_coefficient

    @property
    def ballistic_coefficient(self) -> BallisticCoefficientExtended:
        """
        :return: ballistic coefficient of the projectile
        """
        return self._ballistic_coefficient


class ProjectileWithDimensionsExtended(ProjectileWithDimensions, ProjectileExtended):
    def __init__(self, ballistic_coefficient: BallisticCoefficientExtended,
                 bullet_diameter: unit.Distance,
                 bullet_length: unit.Distance,
                 weight: unit.Weight):
        super(ProjectileWithDimensionsExtended, self).__init__(ballistic_coefficient, bullet_diameter, bullet_length,
                                                               weight)
        self._ballistic_coefficient = ballistic_coefficient
