"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from typing_extensions import Union, List, Optional

# pylint: disable=import-error,no-name-in-module,wildcard-import
from py_ballisticcalc.trajectory_calc import TrajectoryCalc
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.trajectory_data import HitResult
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits
from py_ballisticcalc.interface_config import InterfaceConfigDict, create_interface_config


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    _config: Optional[InterfaceConfigDict] = field(default=None)
    _calc: TrajectoryCalc = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self._calc = TrajectoryCalc(create_interface_config(self._config))

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
             extra_data: bool = False,
             time_step: float = 0.0) -> HitResult:
        """Calculates trajectory
        :param shot: shot parameters (initial position and barrel angle)
        :param trajectory_range: Downrange distance at which to stop computing trajectory
        :param trajectory_step: step between trajectory points to record
        :param extra_data: True => store TrajectoryData for every calculation step;
            False => store TrajectoryData only for each trajectory_step
        :param time_step: (seconds) If > 0 then record TrajectoryData at least this frequently
        """
        trajectory_range = PreferredUnits.distance(trajectory_range)
        if not trajectory_step:
            # need to use raw value in order to avoid unit conversion
            trajectory_step = trajectory_range.raw_value / 10.0
            # default unit for distance is Inch, therefore, specifying value directly in it
            step: Distance = Distance.Inch(trajectory_step)
        else:
            step = PreferredUnits.distance(trajectory_step)
        data = self._calc.trajectory(shot, trajectory_range, step, extra_data, time_step)
        return HitResult(shot, data, extra_data)


__all__ = ('Calculator',)
