"""
This module defines the `EngineProtocol`, a protocol that outlines the
interface for ballistic trajectory calculation engines within the
py_ballisticcalc library.

It specifies the methods that concrete engine implementations must provide
to perform trajectory calculations, access drag model data, and determine
zeroing angles for firearms.
"""

from typing import TypeVar

from typing_extensions import List, Protocol, runtime_checkable

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.unit import Distance, Angular

ConfigT = TypeVar("ConfigT", covariant=True)
TrajectoryDataT = TypeVar("TrajectoryDataT", bound=TrajectoryData)


@runtime_checkable
class EngineProtocol(Protocol[ConfigT, TrajectoryDataT]):
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

    @property
    def table_data(self) -> List[DragDataPoint]:
        """
        Gets the drag model table data.

        Returns:
            List[DragDataPoint]: A list of drag data points.
        """

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False, time_step: float = 0.0) -> List[TrajectoryDataT]:
        """
        Calculates the trajectory of a projectile.

        Args:
            shot_info (Shot): Information about the shot.
            max_range (Distance): The maximum range of the trajectory.
            dist_step (Distance): The distance step for calculations.
            extra_data (bool, optional): Flag to include extra data. Defaults to False.
            time_step (float, optional): The time step for calculations. Defaults to 0.0.

        Returns:
            List[TrajectoryData]: A list of trajectory data points.
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
