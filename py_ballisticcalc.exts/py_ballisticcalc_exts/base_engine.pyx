# cython: freethreading_compatible=True
"""
CythonizedBaseIntegrationEngine

Presently ._integrate() returns dense data in a CythonizedBaseTrajSeq, then .integrate()
    feeds it through the Python TrajectoryDataFilter to build List[TrajectoryData].
"""

from libcpp.vector cimport vector
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport (
    CythonizedBaseTrajData,
    CythonizedBaseTrajSeq,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
    BCLIBC_BaseTrajData_InterpKey,
    BCLIBC_BaseTrajDataHandlerInterface,
    TrajectoryData_from_cpp,
    TrajectoryData_list_from_cpp,
)
from py_ballisticcalc_exts.base_types cimport (
    # types and methods
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag,
    BCLIBC_V3dT,
    BCLIBC_TerminationReason,
)
from py_ballisticcalc_exts.bind cimport (
    # factory funcs
    BCLIBC_Config_from_pyobject,
    BCLIBC_ShotProps_from_pyobject,
    feet_from_c,
    rad_from_c,
    _attribute_to_key,
)

from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.engines.base_engine import create_base_engine_config
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine as _PyBaseIntegrationEngine
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData
from py_ballisticcalc.unit import Angular

__all__ = (
    'CythonizedBaseIntegrationEngine',
)


cdef double _ALLOWED_ZERO_ERROR_FEET = _PyBaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET
cdef double _APEX_IS_MAX_RANGE_RADIANS = _PyBaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS

cdef dict TERMINATION_REASON_MAP = {
    BCLIBC_TerminationReason.NO_TERMINATE: "Unknown",
    BCLIBC_TerminationReason.TARGET_RANGE_REACHED: None,
    BCLIBC_TerminationReason.MINIMUM_VELOCITY_REACHED: RangeError.MinimumVelocityReached,
    BCLIBC_TerminationReason.MAXIMUM_DROP_REACHED: RangeError.MaximumDropReached,
    BCLIBC_TerminationReason.MINIMUM_ALTITUDE_REACHED: RangeError.MinimumAltitudeReached,
}


cdef class CythonizedBaseIntegrationEngine:
    """Implements EngineProtocol"""

    # Expose Python-visible constants to match BaseIntegrationEngine API
    APEX_IS_MAX_RANGE_RADIANS = float(_APEX_IS_MAX_RANGE_RADIANS)
    ALLOWED_ZERO_ERROR_FEET = float(_ALLOWED_ZERO_ERROR_FEET)

    def __init__(self, object config):
        """
        Initializes the engine with the given configuration.

        Args:
            config (BaseEngineConfig): The engine configuration.

        IMPORTANT:
            Avoid calling Python functions inside __init__!
            __init__ is called after __cinit__, so any memory allocated in __cinit__
            that is not referenced in Python will be leaked if __init__ raises an exception.
        """

        self._config = create_base_engine_config(config)

    def __cinit__(self, object config):
        """
        C/C++-level initializer for the engine.
        Override this method to setup integrate_func and other fields.

        NOTE:
            The BCLIBC_BaseEngine is built-in to CythonizedBaseIntegrationEngine,
            so we are need no set it's fields to null
        """
        self._DEFAULT_TIME_STEP = 1.0

    def __dealloc__(CythonizedBaseIntegrationEngine self):
        """Frees any allocated resources."""
        pass

    @property
    def DEFAULT_TIME_STEP(CythonizedBaseIntegrationEngine self):
        return self._DEFAULT_TIME_STEP

    @DEFAULT_TIME_STEP.setter
    def DEFAULT_TIME_STEP(CythonizedBaseIntegrationEngine self, double value):
        self._DEFAULT_TIME_STEP = value

    @property
    def integration_step_count(self) -> int:
        """
        Gets the number of integration steps performed in the last integration.

        Returns:
            int: The number of integration steps.
        """
        return self._this.integration_step_count

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self):
        """Gets the calculation step size in feet."""
        return self.DEFAULT_TIME_STEP * self._this.config.cStepMultiplier

    def find_max_range(self, object shot_info, tuple angle_bracket_deg = (0, 90)):
        """
        Finds the maximum range along shot_info.look_angle,
        and the launch angle to reach it.

        Args:
            shot_info (Shot): The shot information.
            angle_bracket_deg (Tuple[float, float], optional):
                The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum slant range and the launch angle to reach it.
        """
        cdef BCLIBC_MaxRangeResult res = self._find_max_range(
            shot_info,
            angle_bracket_deg[0],
            angle_bracket_deg[1]
        )
        return feet_from_c(res.max_range_ft), rad_from_c(res.angle_at_max_rad)

    def find_zero_angle(self, object shot_info, object distance, bint lofted = False):
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
        cdef double zero_angle = self._find_zero_angle(shot_info, distance._feet, lofted)
        return rad_from_c(zero_angle)

    def find_apex(self, object shot_info) -> TrajectoryData:
        """
        Finds the apex of the trajectory, where apex is defined as the point
        where the vertical component of velocity goes from positive to negative.

        Args:
            shot_info (Shot): The shot information.

        Returns:
            TrajectoryData: The trajectory data at the apex.
        """
        cdef BCLIBC_TrajectoryData apex = self._find_apex(shot_info)
        return TrajectoryData_from_cpp(apex)

    def zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        object distance
    ) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance.
        First tries iterative approach; if that fails falls back on _find_zero_angle.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        self._init_trajectory(shot_info)
        cdef:
            double result
        result = self._this.zero_angle_with_fallback(
            distance._feet,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
        )
        return rad_from_c(result)

    def integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        object max_range,
        object dist_step = None,
        float time_step = 0.0,
        int filter_flags = 0,
        bint dense_output = False,
        **kwargs
    ) -> HitResult:
        """
        Integrates the trajectory for the given shot.

        Args:
            shot_info (Shot): The shot information.
            max_range (Distance):
                Maximum range of the trajectory (if float then treated as feet).
            dist_step (Optional[Distance]):
                Distance step for recording RANGE TrajectoryData rows.
            time_step (float, optional):
                Time step for recording trajectory data. Defaults to 0.0.
            filter_flags (Union[TrajFlag, int], optional):
                Flags to filter trajectory data. Defaults to TrajFlag.RANGE.
            dense_output (bool, optional):
                If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult: Object for describing the trajectory.
        """
        cdef:
            object props
            object termination_reason = None
            list[object] trajectory = None
            BCLIBC_TerminationReason reason
            double range_limit_ft = max_range._feet
            double range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft
            vector[BCLIBC_TrajectoryData] filtered_records
            CythonizedBaseTrajSeq dense_trajectory

        if dense_output:
            dense_trajectory = CythonizedBaseTrajSeq()

        self._init_trajectory(shot_info)

        self._this.integrate_filtered(
            range_limit_ft,
            range_step_ft,
            time_step,
            <BCLIBC_TrajFlag>filter_flags,
            filtered_records,
            reason,
            &dense_trajectory._this if dense_output else NULL,
        )

        trajectory = TrajectoryData_list_from_cpp(filtered_records)

        # Extract termination_reason from the result
        termination_reason = TERMINATION_REASON_MAP.get(reason)

        if termination_reason is not None:
            termination_reason = RangeError(termination_reason, trajectory)

        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()  # Add missing calc_step attribute
        return HitResult(
            props,
            trajectory,
            dense_trajectory if dense_output else None,
            filter_flags != BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_NONE,
            termination_reason
        )

    def integrate_raw_at(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        str key_attribute,
        double target_value
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
        cdef BCLIBC_BaseTrajData_InterpKey key = _attribute_to_key(key_attribute)
        cdef CythonizedBaseTrajData raw_data = CythonizedBaseTrajData()
        cdef BCLIBC_TrajectoryData full_data
        cdef object py_full_data

        self._integrate_raw_at(shot_info, key, target_value, raw_data._this, full_data)

        py_full_data = TrajectoryData_from_cpp(full_data)
        return raw_data, py_full_data

    cdef inline double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        double angle_rad,
        double target_x_ft,
        double target_y_ft
    ):
        """
        Target miss (feet) for given launch angle using CythonizedBaseTrajSeq.
        Attempts to avoid Python exceptions in the hot path by pre-checking reach.

        Args:
            angle_rad (double): Launch angle in radians.
            target_x_ft (double): Target X coordinate in feet.
            target_y_ft (double): Target Y coordinate in feet.

        Returns:
            double: The miss distance in feet (positive if overshot, negative if undershot).
        """
        return self._this.error_at_distance(
            angle_rad,
            target_x_ft,
            target_y_ft,
        )

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    ):
        """
        Converts Shot properties into floats dimensioned in internal units.

        Args:
            shot_info (Shot): Information about the shot.

        Returns:
            BCLIBC_ShotProps*: Pointer to the initialized shot properties.
        """

        # hack to reload config if it was changed explicit on existed instance
        self._this.config = BCLIBC_Config_from_pyobject(self._config)
        self._this.gravity_vector = BCLIBC_V3dT(.0, self._this.config.cGravityConstant, .0)

        self._table_data = shot_info.ammo.dm.drag_table
        # Build C shot struct with robust cleanup on any error that follows

        self._this.shot = BCLIBC_ShotProps_from_pyobject(shot_info, self.get_calc_step())

        return &self._this.shot

    cdef void _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        BCLIBC_ZeroInitialData &out,
    ):
        """
        Initializes the zero calculation for the given shot and distance.
        Handles edge cases.

        Args:
            distance (double): The distance to the target in feet.

        Returns:
            tuple: (status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
            where status is: 0 = CONTINUE, 1 = DONE (early return with look_angle_rad)
        """
        self._this.init_zero_calculation(
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            out,
        )

    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance,
        bint lofted
    ):
        """
        Find zero angle using Ridder's method for guaranteed convergence.

        Args:
            distance (double): The distance to the target in feet.
            lofted (bint): Whether the shot is lofted.

        Returns:
            double: The calculated zero angle in radians.
        """
        self._init_trajectory(shot_info)
        return self._this.find_zero_angle(
            distance,
            lofted,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
        )

    cdef BCLIBC_MaxRangeResult _find_max_range(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double low_angle_deg,
        double high_angle_deg,
    ):
        """
        Internal function to find the maximum slant range via golden-section search.

        Args:
            props (ShotProps): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional):
                The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum slant range and the launch angle to reach it.
        """
        self._init_trajectory(shot_info)
        return self._this.find_max_range(
            low_angle_deg,
            high_angle_deg,
            _APEX_IS_MAX_RANGE_RADIANS,
        )

    cdef BCLIBC_TrajectoryData _find_apex(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
    ):
        """
        Internal implementation to find the apex of the trajectory.

        Returns:
            BCLIBC_TrajectoryData: The trajectory data at the apex.
        """
        self._init_trajectory(shot_info)
        cdef BCLIBC_BaseTrajData apex = BCLIBC_BaseTrajData()
        self._this.find_apex(apex)
        return BCLIBC_TrajectoryData(
            self._this.shot,
            apex,
            BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_APEX
        )

    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance
    ):
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            props (BCLIBC_ShotProps): Shot parameters
            distance (double): Sight distance to zero (i.e., along Shot.look_angle), units=feet,
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        self._init_trajectory(shot_info)
        return self._this.zero_angle(
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
        )

    cdef void _integrate_raw_at(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        BCLIBC_BaseTrajData_InterpKey key,
        double target_value,
        BCLIBC_BaseTrajData &raw_data,
        BCLIBC_TrajectoryData &full_data
    ):
        """
        Internal C-level method to initialize the trajectory and call the
        C++ engine's integrate_at function.

        This method handles the low-level data passing and error wrapping.

        Args:
            shot_info (object): Trajectory initialization data.
            key (BCLIBC_BaseTrajData_InterpKey): The C++ enumeration key defining
                the attribute for interpolation.
            target_value (double): The target value for the interpolation key.
            raw_data (BCLIBC_BaseTrajData&): Reference to the C++ structure to
                store the raw interpolated data.
            full_data (BCLIBC_TrajectoryData&): Reference to the C++ structure
                to store the full processed data.

        Raises:
            InterceptionError: If the underlying C++ integration fails to find
                the target point (e.g., due to insufficient range or data issues).
            SolverRuntimeError: If some other internal error occured
        """
        self._init_trajectory(shot_info)
        self._this.integrate_at(
            key,
            target_value,
            raw_data,
            full_data,
        )

    cdef void _integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double range_limit_ft,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ):
        """
        Internal method to perform trajectory integration.

        Args:
            range_limit_ft (double): Maximum range limit in feet.
            range_step_ft (double): Range step in feet.
            filter_flags (BCLIBC_TrajFlag): Flags to filter trajectory data.

        Returns:
            tuple: (CythonizedBaseTrajSeq, str or None)
                CythonizedBaseTrajSeq: The trajectory sequence.
                BCLIBC_TerminationReason: Termination reason if applicable.
        """
        self._init_trajectory(shot_info)
        self._this.integrate(range_limit_ft, handler, reason)
