"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from typing_extensions import Union, List

# pylint: disable=import-error,no-name-in-module,wildcard-import
# from py_ballisticcalc.backend import TrajectoryCalc
from py_ballisticcalc.trajectory_calc import TrajectoryCalc
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.trajectory_data import HitResult
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    _calc: TrajectoryCalc = field(init=False, repr=False, compare=False)

    @property
    def cdm(self) -> List[DragDataPoint]:
        """returns custom drag function based on input data"""
        return self._calc.table_data

    def barrel_elevation_for_target(self, shot: Shot, target_distance: Union[float, Distance]) -> Angular:
        """Calculates barrel elevation to hit target at zero_distance.
        :param shot: Shot instance for which calculate barrel elevation is
        :param target_distance: Look-distance to "zero," which is point we want to hit.
            This is the distance that a rangefinder would return with no ballistic adjustment.
            NB: Some rangefinders offer an adjusted distance based on inclinometer measurement.
                However, without a complete ballistic model these can only approximate the effects
                on ballistic trajectory of shooting uphill or downhill.  Therefore:
                For maximum accuracy, use the raw sight distance and look_angle as inputs here.
        """
        self._calc = TrajectoryCalc(shot.ammo)
        target_distance = PreferredUnits.distance(target_distance)
        total_elevation = self._calc.zero_angle(shot, target_distance)
        return Angular.Radian(
            (total_elevation >> Angular.Radian) - (shot.look_angle >> Angular.Radian)
        )

    def set_weapon_zero(self, shot: Shot, zero_distance: Union[float, Distance]) -> Angular:
        """Sets shot.weapon.zero_elevation so that it hits a target at zero_distance.
        :param shot: Shot instance from which we take a zero
        :param zero_distance: Look-distance to "zero," which is point we want to hit.
        """
        shot.weapon.zero_elevation = self.barrel_elevation_for_target(shot, zero_distance)
        return shot.weapon.zero_elevation

    def fire(self, shot: Shot, trajectory_range: Union[float, Distance],
             trajectory_step: Union[float, Distance] = 0,
             extra_data: bool = False) -> HitResult:
        """Calculates trajectory
        :param shot: shot parameters (initial position and barrel angle)
        :param trajectory_range: Downrange distance at which to stop computing trajectory
        :param trajectory_step: step between trajectory points to record
        :param extra_data: True => store TrajectoryData for every calculation step;
            False => store TrajectoryData only for each trajectory_step
        """
        trajectory_range = PreferredUnits.distance(trajectory_range)
        if not trajectory_step:
            trajectory_step = trajectory_range.unit_value / 10.0
        step: Distance = PreferredUnits.distance(trajectory_step)
        self._calc = TrajectoryCalc(shot.ammo)
        data = self._calc.trajectory(shot, trajectory_range, step, extra_data)
        return HitResult(shot, data, extra_data)


__all__ = ('Calculator',)
