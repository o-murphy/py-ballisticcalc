"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from .conditions import Atmo, Shot
from .munition import Weapon, Ammo
# pylint: disable=import-error,no-name-in-module
from .backend import *
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

    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False, default=None)

    @property
    def cdm(self):
        """returns custom drag function based on input data"""
        return self._calc.cdm

    def set_weapon_zero(self, zero_distance: [float, Distance],
                        zero_look_angle: Angular = Angular.Degree(0)) -> Angular:
        """Calculates barrel elevation to hit target at zero_distance.

        :param zero_distance: Sight-line distance to "zero," which is point we want to hit.
            This is the distance that a rangefinder would return with no ballistic adjustment.
            NB: Some rangefinders offer an adjusted distance based on inclinometer measurement.
                However, without a complete ballistic model these can only approximate the effects
                on ballistic trajectory of shooting uphill or downhill.  Therefore:
                For maximum accuracy, use the raw sight distance and look_angle as inputs here.
        :param zero_look_angle: Angle between sight line and horizontal when sighting zero target.
        """
        self._calc = TrajectoryCalc(self.ammo)
        zero_total_elevation = self._calc.zero_angle(self.weapon, self.zero_atmo,
                                                    zero_distance, zero_look_angle)
        self.weapon.zero_elevation = Angular.Radian((zero_total_elevation >> Angular.Radian)
                                                     - (zero_look_angle >> Angular.Radian))
        return self.weapon.zero_elevation

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
        trajectory_range = Settings.Units.distance(trajectory_range)
        step = Settings.Units.distance(trajectory_step)
        self._calc = TrajectoryCalc(self.ammo)
        data = self._calc.trajectory(shot, trajectory_range, step, extra_data)
        return HitResult(shot, data, extra_data)
