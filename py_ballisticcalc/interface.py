"""Implements basic interface for the ballistics calculator"""
import math
from dataclasses import dataclass, field

from .conditions import Atmo, Wind, Shot
from .munition import Weapon, Ammo
from .settings import Settings as Set
from .trajectory_calc import TrajectoryCalc
from .trajectory_data import TrajectoryData
from .unit import Angular, Distance, is_unit

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo

    _elevation: Angular = field(init=False, repr=True, compare=False, default=None)
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False, default=None)

    @property
    def elevation(self):
        return self._elevation

    @property
    def cdm(self):
        return self._calc.cdm

    def __post_init__(self):
        """Creates calculator instance with specified ammo"""
        self._calc = TrajectoryCalc(self.ammo)

    def update_elevation(self):
        """Recalculates barrel elevation for weapon and zero atmo"""
        self._elevation = self._calc.sight_angle(self.weapon, self.zero_atmo)

    def trajectory(self, shot: Shot, current_atmo: Atmo, winds: list[Wind]) -> list:
        """Calculates trajectory with current conditions
        :param shot: shot parameters
        :param current_atmo: current atmosphere conditions
        :param winds: current winds list
        :return: trajectory table
        """
        if not self._elevation and not shot.sight_angle:
            self.update_elevation()
            shot.sight_angle = self._elevation
        data = self._calc.trajectory(self.weapon, current_atmo, shot, winds)
        return data

    def zero_given_elevation(self, elevation: [float, Angular],
                             winds: list[Wind] = None) -> TrajectoryData:
        """Find the zero distance for a given barrel elevation"""

        if not winds:
            winds = [Wind()]

        elevation = elevation if is_unit(elevation) else Set.Units.angular
        shot = Shot(1000, 100, sight_angle=elevation)
        data = self._calc.trajectory(self.weapon, self.zero_atmo, shot, winds)
        # No downrange zero found, so just return starting row
        return data[1] if len(data) > 1 else data[0]

    @staticmethod
    def danger_space(trajectory: TrajectoryData, target_height: [float, Distance]) -> Distance:
        """Given a TrajectoryData row, we have the angle of travel
        of bullet at that point in its trajectory, which is at distance *d*.
        "Danger Space" is defined for *d* and for a target of height
        `targetHeight` as the error range for the target, meaning
        if the trajectory hits the center of the target when
        the target is exactly at *d*, then "Danger Space" is the distance
        before or after *d* across which the bullet would still hit somewhere on the target.
        (This ignores windage; vertical only.)

        :param trajectory: single point from trajectory table
        :param target_height: error range for the target
        :return: danger space for target_height specified
        """
        target_height = (target_height if is_unit(target_height)
                         else Set.Units.target_height(target_height)) >> Distance.Yard
        traj_angle_tan = math.tan(trajectory.angle >> Angular.Radian)
        return Distance.Yard(-(target_height / traj_angle_tan))
