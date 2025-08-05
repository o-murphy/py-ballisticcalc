"""
This module defines the `EngineProtocol`, a protocol that outlines the
interface for ballistic trajectory calculation engines within the
py_ballisticcalc library.

It specifies the methods that concrete engine implementations must provide
to perform trajectory calculations, access drag model data, and determine
zeroing angles for firearms.
"""

from typing import TypeVar, Optional

from typing_extensions import Protocol, runtime_checkable

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag
from py_ballisticcalc.unit import Distance, Angular

ConfigT = TypeVar("ConfigT", covariant=True)


@runtime_checkable
class EngineProtocol(Protocol[ConfigT]):
    """
    Defines the interface for a ballistic trajectory calculation engine.

    This protocol outlines the methods that any concrete ballistic engine
    implementation should provide to perform trajectory calculations,
    retrieve drag model information, and determine zeroing angles.
    """

    def __init__(self, _config: ConfigT):
        """
        Initializes the TrajectoryCalc class.

        Args:
            _config (Config): The configuration object.
        """

    def integrate(self, shot_info: Shot,
                  max_range: Distance,
                  dist_step: Optional[Distance] = None,
                  time_step: float = 0.0,
                  filter_flags: TrajFlag = TrajFlag.NONE,
                  dense_output: bool = False,
                  **kwargs) -> HitResult:
        """
        Calculate trajectory for specified shot.  Requirements for the return List:
        - Starts with the initial conditions of the shot.
        - If filter_flags==TrajFlag.NONE, then the last List element must be TrajectoryData where:
            - .distance = maximum_range if reached, else last calculated point.
        - If filter_flags & TrajFlag.RANGE, then return must include a RANGE entry for each record_step reached.
        - If time_step > 0, must also include RANGE entries per that spec.
        - For each other filter_flag: Return list must include a row with the flag if it exists in the trajectory.
            Do not duplicate rows: If two flags occur at the exact same time, mark the row with both flags.

        Args:
            shot_info (Shot): Information about the shot.
            max_range (Distance): The maximum range of the trajectory.
            dist_step (Distance, optional): The distance step for calculations. Defaults to None.
            extra_data (bool, optional): Flag to include extra data. Defaults to False.
            time_step (float, optional): The time step for calculations. Defaults to 0.0.
            dense_output (bool, optional): If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult: Object for describing the trajectory.
        """

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Zero distance

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """
