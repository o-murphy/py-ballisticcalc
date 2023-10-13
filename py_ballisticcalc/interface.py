"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from .conditions import Atmo, Shot
from .munition import Weapon, Ammo
# pylint: disable=import-error,no-name-in-module
from .trajectory_calc import TrajectoryCalc
from .trajectory_data import HitResult
from .unit import Angular, Distance
from .settings import Settings

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo = field(default_factory=Atmo.icao)
    _elevation: Angular = field(init=False, repr=True, compare=False,
                                default_factory=lambda: Angular.Degree(0))
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False, default=None)

    def __post_init__(self):
        self.calculate_elevation()

    @property
    def elevation(self):
        """get current barrel elevation"""
        return self._elevation

    @property
    def cdm(self):
        """returns custom drag function based on input data"""
        return self._calc.cdm

    def calculate_elevation(self):
        """Recalculates barrel elevation for weapon and zero atmo"""
        self._calc = TrajectoryCalc(self.ammo)
        self._elevation = self._calc.zero_angle(self.weapon, self.zero_atmo)

    def fire(self, shot: Shot, trajectory_step: [float, Distance],
             extra_data: bool = False) -> HitResult:
        """Calculates trajectory with current conditions
        :param shot: shot parameters
        :param trajectory_step: step between trajectory points
        :param filter_flags: filter trajectory points
        :return: trajectory table
        """
        step = Settings.Units.distance(trajectory_step)
        self._calc = TrajectoryCalc(self.ammo)
        if not shot.zero_angle:
            shot.zero_angle = self._elevation
        data = self._calc.trajectory(self.weapon, shot, step, extra_data)
        return HitResult(data, extra_data)

    # @staticmethod
    # def danger_space(trajectory: TrajectoryData, target_height: [float, Distance]) -> Distance:
    #     """Given a TrajectoryData row, we have the angle of travel
    #     of bullet at that point in its trajectory, which is at distance *d*.
    #     "Danger Space" is defined for *d* and for a target of height
    #     `targetHeight` as the error range for the target, meaning
    #     if the trajectory hits the center of the target when
    #     the target is exactly at *d*, then "Danger Space" is the distance
    #     before or after *d* across which the bullet would still hit somewhere on the target.
    #     (This ignores windage; vertical only.)
    #
    #     :param trajectory: single point from trajectory table
    #     :param target_height: error range for the target
    #     :return: danger space for target_height specified
    #     """
    #
    #     target_height = (target_height if is_unit(target_height)
    #                      else Set.Units.target_height(target_height)) >> Distance.Yard
    #     traj_angle_tan = math.tan(trajectory.angle >> Angular.Radian)
    #     return Distance.Yard(-(target_height / traj_angle_tan))
