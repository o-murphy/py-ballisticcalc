"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.base_engine`
to improve IDE completion for the Cythonized API.
"""

from typing import Any

from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag, TrajectoryData
from py_ballisticcalc.unit import Angular, Distance
from py_ballisticcalc_exts.traj_data import CythonizedBaseTrajData
from py_ballisticcalc.exceptions import SolverRuntimeError

class InterceptionError(SolverRuntimeError):
    def __init__(self, *args, last_data: tuple[CythonizedBaseTrajData, TrajectoryData]): ...
    @property
    def last_data(self) -> tuple[CythonizedBaseTrajData, TrajectoryData]: ...

class CythonizedBaseIntegrationEngine(EngineProtocol[BaseEngineConfigDict]):
    """Base Cython wrapper for C/С++ based binary engine. Implements EngineProtocol"""

    # Class constants
    APEX_IS_MAX_RANGE_RADIANS: float
    ALLOWED_ZERO_ERROR_FEET: float

    def __init__(self, config: BaseEngineConfigDict | None) -> None:
        """
        Initializes the engine with the given configuration.

        Args:
            config (BaseEngineConfig): The engine configuration.

        IMPORTANT:
            Avoid calling Python functions inside `__init__`!
            `__init__` is called after `__cinit__`, so any memory allocated in `__cinit__`
            that is not referenced in Python will be leaked if `__init__` raises an exception.
        """
        ...

    def __cinit__(self, config: BaseEngineConfigDict | None) -> None:
        """
        C/C++-level initializer for the engine.
        Override this method to setup integrate_func and other fields.

        NOTE:
            The BCLIBC_BaseEngine is built-in to CythonizedBaseIntegrationEngine,
            so we are need no set it's fields to null
        """
        ...

    def __dealloc__(self) -> None:
        """Frees any allocated resources."""
        ...

    @property
    def DEFAULT_TIME_STEP(self) -> float: ...
    @DEFAULT_TIME_STEP.setter
    def DEFAULT_TIME_STEP(self, value: float) -> None: ...
    @property
    def integration_step_count(self) -> int:
        """
        Gets the number of integration steps performed in the last integration.

        Returns:
            int: The number of integration steps.
        """
        ...

    def find_max_range(
        self, shot_info: Shot, angle_bracket_deg: tuple[float, float] = (0, 90)
    ) -> tuple[Distance, Angular]:
        """
        Finds the maximum range along shot_info.look_angle,
        and the launch angle to reach it.

        Args:
            shot_info (Shot): The shot information.
            angle_bracket_deg (tuple[float, float], optional):
                The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            tuple[Distance, Angular]: The maximum slant range and the launch angle to reach it.
        """
        ...

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
        using unimodal root-finding that is guaranteed to succeed if a solution exists.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.
            lofted (bool): Whether the shot is lofted.

        Returns:
            Angular: The required barrel elevation angle.
        """
        ...

    def find_apex(self, shot_info: Shot) -> TrajectoryData:
        """
        Finds the apex of the trajectory, where apex is defined as the point
        where the vertical component of velocity goes from positive to negative.

        Args:
            shot_info (Shot): The shot information.

        Returns:
            TrajectoryData: The trajectory data at the apex.
        """
        ...

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance.
        First tries iterative approach; if that fails falls back on _find_zero_angle.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        ...

    def integrate(
        self,
        shot_info: Shot,
        max_range: Distance,
        dist_step: Distance | None = None,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = 0,
        dense_output: bool = False,
        **kwargs: Any,
    ) -> HitResult:
        """
        Integrates the trajectory for the given shot.

        Args:
            shot_info (Shot): The shot information.
            max_range (Distance):
                Maximum range of the trajectory (if float then treated as feet).
            dist_step (Distance | None):
                Distance step for recording RANGE TrajectoryData rows.
            time_step (float, optional):
                Time step for recording trajectory data. Defaults to 0.0.
            filter_flags (TrajFlag | int, optional):
                Flags to filter trajectory data. Defaults to TrajFlag.RANGE.
            dense_output (bool, optional):
                If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult: Object for describing the trajectory.
        """
        ...

    def integrate_raw_at(
        self, shot_info: Shot, key_attribute: str, target_value: float
    ) -> tuple[CythonizedBaseTrajData, TrajectoryData]:
        """
        Integrates the trajectory until a specified attribute reaches a target value
        and returns the interpolated data point.

        This method initializes the trajectory using the provided shot information,
        performs integration using the underlying C++ engine's 'integrate_at' function,
        and handles the conversion of C++ results back to Python objects.

        Args:
            shot_info (object): Information required to initialize the trajectory
                (e.g., muzzle velocity, drag model).
            key_attribute (str): The name of the attribute to track, such as
                'time', 'mach', or a vector component like 'position.z'.
            target_value (float): The value the 'key_attribute' must reach for
                the integration to stop and interpolation to occur.

        Returns:
            tuple[CythonizedBaseTrajData, TrajectoryData]:
                A tuple containing:
                - CythonizedBaseTrajData: The interpolated raw data point.
                - TrajectoryData: The fully processed trajectory data point.

        Raises:
            InterceptionError: If the underlying C++ integration fails to find
                the target point (e.g., due to insufficient range or data issues).
            SolverRuntimeError: If some other internal error occured
        """
        ...
