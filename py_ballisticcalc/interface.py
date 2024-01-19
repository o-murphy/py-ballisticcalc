"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from .conditions import Shot
# pylint: disable=import-error,no-name-in-module
from .backend import *
from .trajectory_data import HitResult
from .unit import Angular, Distance
from .settings import Settings

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    _calc: TrajectoryCalc = field(init=False, repr=False, compare=False, default=None)

    @property
    def cdm(self):
        """returns custom drag function based on input data"""
        return self._calc.cdm

    def set_weapon_zero(self, shot: Shot, zero_distance: [float, Distance]) -> Angular:
        """Calculates barrel elevation to hit target at zero_distance.

        :param zero_distance: Sight-line distance to "zero," which is point we want to hit.
            This is the distance that a rangefinder would return with no ballistic adjustment.
            NB: Some rangefinders offer an adjusted distance based on inclinometer measurement.
                However, without a complete ballistic model these can only approximate the effects
                on ballistic trajectory of shooting uphill or downhill.  Therefore:
                For maximum accuracy, use the raw sight distance and look_angle as inputs here.
        :param zero_look_angle: Angle between sight line and horizontal when sighting zero target.
        """
        self._calc = TrajectoryCalc(shot.ammo)
        zero_distance = Settings.Units.distance(zero_distance)
        zero_total_elevation = self._calc.zero_angle(shot.weapon, shot.atmo,
                                                    zero_distance, shot.look_angle)
        shot.weapon.zero_elevation = Angular.Radian((zero_total_elevation >> Angular.Radian)
                                                     - (shot.look_angle >> Angular.Radian))
        return shot.weapon.zero_elevation

    def fire(self, shot: Shot, trajectory_range: [float, Distance],
             trajectory_step: [float, Distance] = 0,
             extra_data: bool = False) -> HitResult:
        """Calculates trajectory
        :param shot: shot parameters (initial position and barrel angle)
        :param range: Downrange distance at which to stop computing trajectory
        :param trajectory_step: step between trajectory points to record
        :param extra_data: True => store TrajectoryData for every calculation step;
            False => store TrajectoryData only for each trajectory_step
        """
        if not trajectory_step:
            trajectory_step = trajectory_range / 10.0
        trajectory_range = Settings.Units.distance(trajectory_range)
        step = Settings.Units.distance(trajectory_step)
        self._calc = TrajectoryCalc(shot.ammo)
        data = self._calc.trajectory(shot, trajectory_range, step, extra_data)
        return HitResult(shot, data, extra_data)
