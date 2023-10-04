"""Implements basic interface for the ballistics calculator"""

from dataclasses import dataclass, field

from .trajectory_calc import TrajectoryCalc
from .conditions import Atmo, Wind, Shot
from .munition import Weapon, Ammo
from .unit import Angular

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo

    _elevation: Angular = field(init=False, repr=True, compare=False)
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False)

    def __post_init__(self):
        """Creates calculator instance with specified ammo"""
        self._calc = TrajectoryCalc(self.ammo)

    def update_elevation(self):
        """Recalculates barrel elevation for weapon and zero atmo"""
        self._elevation = self._calc.sight_angle(self.weapon, self.zero_atmo)

    def trajectory(self, shot: Shot, current_atmo: Atmo, winds: list[Wind],
                   # as_pandas: bool = False
                   ) -> list:
        """Calculates trajectory with current conditions
        :param shot: shot parameters
        :param current_atmo: current atmosphere conditions
        :param winds: current winds list
        :return: trajectory table
        """
        if not self._elevation:
            self.update_elevation()
        shot.sight_angle = self._elevation
        data = self._calc.trajectory(self.weapon, current_atmo, shot, winds)
        # if as_pandas:
        #     return self._to_dataframe(data)
        return data
