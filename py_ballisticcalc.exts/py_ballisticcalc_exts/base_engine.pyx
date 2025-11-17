# cython: freethreading_compatible=True
"""
CythonizedBaseIntegrationEngine

Presently ._integrate() returns dense data in a BaseTrajSeqT, then .integrate()
    feeds it through the Python TrajectoryDataFilter to build List[TrajectoryData].
"""
# (Avoid importing cpython.exc; raise Python exceptions directly in cdef functions where needed)
from libcpp.vector cimport vector
from cython.operator cimport dereference as deref, preincrement as inc
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport (
    BaseTrajSeqT,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
)
from py_ballisticcalc_exts.base_types cimport (
    # types and methods
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.bind cimport (
    # factory funcs
    BCLIBC_Config_from_pyobject,
    BCLIBC_ShotProps_from_pyobject,
    feet_from_c,
    rad_from_c,
    v3d_to_vector,
)
from py_ballisticcalc_exts.error_stack cimport (
    BCLIBC_StatusCode,
    BCLIBC_ErrorSource,
    BCLIBC_ErrorFrame,
    BCLIBC_ErrorType,
    BCLIBC_ErrorStack,
    BCLIBC_ErrorStack_lastErr,
    BCLIBC_ErrorStack_toString,
)
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.engines.base_engine import create_base_engine_config
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine as _PyBaseIntegrationEngine
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData
from py_ballisticcalc.unit import Angular

__all__ = (
    'CythonizedBaseIntegrationEngine',
)


cdef double _ALLOWED_ZERO_ERROR_FEET = _PyBaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET
cdef double _APEX_IS_MAX_RANGE_RADIANS = _PyBaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS


cdef dict ERROR_TYPE_TO_EXCEPTION = {
    BCLIBC_ErrorType.INPUT_ERROR: TypeError,
    BCLIBC_ErrorType.ZERO_FINDING_ERROR: ZeroFindingError,
    BCLIBC_ErrorType.OUT_OF_RANGE_ERROR: OutOfRangeError,
    BCLIBC_ErrorType.VALUE_ERROR: ValueError,
    BCLIBC_ErrorType.INDEX_ERROR: IndexError,
    BCLIBC_ErrorType.BASE_TRAJ_INTERP_KEY_ERROR: AttributeError,
    BCLIBC_ErrorType.MEMORY_ERROR: MemoryError,
    BCLIBC_ErrorType.ARITHMETIC_ERROR: ArithmeticError,
    BCLIBC_ErrorType.RUNTIME_ERROR: SolverRuntimeError,
}

cdef dict TERMINATION_REASON_MAP = {
    BCLIBC_TerminationReason.MINIMUM_VELOCITY_REACHED: RangeError.MinimumVelocityReached,
    BCLIBC_TerminationReason.MAXIMUM_DROP_REACHED: RangeError.MaximumDropReached,
    BCLIBC_TerminationReason.MINIMUM_ALTITUDE_REACHED: RangeError.MinimumAltitudeReached,
}

cdef class CythonizedBaseIntegrationEngine:
    """Implements EngineProtocol"""
    # Expose Python-visible constants to match BaseIntegrationEngine API
    APEX_IS_MAX_RANGE_RADIANS = float(_APEX_IS_MAX_RANGE_RADIANS)
    ALLOWED_ZERO_ERROR_FEET = float(_ALLOWED_ZERO_ERROR_FEET)

    def __init__(self, object _config):
        """
        Initializes the engine with the given configuration.

        Args:
            _config (BaseEngineConfig): The engine configuration.

        IMPORTANT:
            Avoid calling Python functions inside __init__!
            __init__ is called after __cinit__, so any memory allocated in __cinit__
            that is not referenced in Python will be leaked if __init__ raises an exception.
        """

        self._config = create_base_engine_config(_config)

    def __cinit__(self, object _config):
        """
        C-level initializer for the engine.
        Override this method to setup integrate_func_ptr and other fields.

        NOTE:
            The BCLIBC_Engine is built-in to CythonizedBaseIntegrationEngine,
            so we are need no set it's fields to null
        """
        # self._this.gravity_vector = BCLIBC_V3dT(.0, .0, .0)
        # self._this.integration_step_count = 0
        pass

    def __dealloc__(CythonizedBaseIntegrationEngine self):
        """Frees any allocated resources."""
        pass

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
        return self._this.config.cStepMultiplier

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
        cdef BCLIBC_BaseTrajData result = self._find_apex(shot_info)
        cdef object props = ShotProps.from_shot(shot_info)
        return TrajectoryData.from_props(
            props,
            result.time,
            v3d_to_vector(&result.position),
            v3d_to_vector(&result.velocity),
            result.mach)

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
            BCLIBC_StatusCode status
            double result
            BCLIBC_OutOfRangeError range_error = {}
            BCLIBC_ZeroFindingError zero_error = {}

        status = self._this.zero_angle_with_fallback(
            distance._feet,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            &result,
            &range_error,
            &zero_error,
        )

        if status == BCLIBC_StatusCode.SUCCESS:
            return rad_from_c(result)

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        if err.src == BCLIBC_ErrorSource.INIT_ZERO:
            self._raise_on_init_zero_error(err, &range_error)
        if err.src == BCLIBC_ErrorSource.FIND_ZERO_ANGLE:
            self._raise_on_init_zero_error(err, &range_error)
            self._raise_on_zero_finding_error(err, &zero_error)
        self._raise_solver_runtime_error(err)

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
            BCLIBC_TerminationReason reason
            BCLIBC_StatusCode status
            double range_limit_ft = max_range._feet
            double range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft
            vector[BCLIBC_TrajectoryData] records
            BaseTrajSeqT trajectory = BaseTrajSeqT()

        self._init_trajectory(shot_info)
        cdef const BCLIBC_ErrorFrame *err

        status = self._this.integrate_filtered(
            range_limit_ft,
            range_step_ft,
            time_step,
            <BCLIBC_TrajFlag>filter_flags,
            &records,
            &trajectory._this,
            &reason,
        )

        if status == BCLIBC_StatusCode.ERROR:
            err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
            self._raise_solver_runtime_error(err)

        # Extract termination_reason from the result
        termination_reason = TERMINATION_REASON_MAP.get(reason)

        if termination_reason is not None:
            termination_reason = RangeError(termination_reason, TrajectoryData_list_from_cpp(&records))

        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()  # Add missing calc_step attribute
        return HitResult(
            props,
            TrajectoryData_list_from_cpp(&records),
            trajectory if dense_output else None,
            filter_flags != BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_NONE,
            termination_reason
        )

    cdef inline double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        double angle_rad,
        double target_x_ft,
        double target_y_ft
    ):
        """
        Target miss (feet) for given launch angle using BaseTrajSeqT.
        Attempts to avoid Python exceptions in the hot path by pre-checking reach.

        Args:
            angle_rad (double): Launch angle in radians.
            target_x_ft (double): Target X coordinate in feet.
            target_y_ft (double): Target Y coordinate in feet.

        Returns:
            double: The miss distance in feet (positive if overshot, negative if undershot).
        """
        cdef double out_error_ft
        cdef BCLIBC_StatusCode status = self._this.error_at_distance(
            angle_rad,
            target_x_ft,
            target_y_ft,
            &out_error_ft
        )
        
        if status == BCLIBC_StatusCode.SUCCESS:
            return out_error_ft
        
        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        self._raise_solver_runtime_error(err)

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

    cdef BCLIBC_StatusCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        BCLIBC_ZeroInitialData *out,
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
        cdef BCLIBC_OutOfRangeError err_data = {}
        cdef BCLIBC_StatusCode status = self._this.init_zero_calculation(
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            out,
            &err_data,
        )

        if status == BCLIBC_StatusCode.SUCCESS:
            return status

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        if err.src == BCLIBC_ErrorSource.INIT_ZERO:
            self._raise_on_init_zero_error(err, &err_data)
        self._raise_solver_runtime_error(err)

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
        cdef BCLIBC_OutOfRangeError range_error = {}
        cdef BCLIBC_ZeroFindingError zero_error = {}
        cdef double result
        cdef BCLIBC_StatusCode status = self._this.find_zero_angle(
            distance,
            lofted,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            &result,
            &range_error,
            &zero_error,
        )
        if status == BCLIBC_StatusCode.SUCCESS:
            return result

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        if err.src == BCLIBC_ErrorSource.INIT_ZERO:
            self._raise_on_init_zero_error(err, &range_error)
        if err.src == BCLIBC_ErrorSource.FIND_ZERO_ANGLE:
            self._raise_on_init_zero_error(err, &range_error)
            self._raise_on_zero_finding_error(err, &zero_error)
        self._raise_solver_runtime_error(err)

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
        cdef BCLIBC_MaxRangeResult result = {}
        cdef BCLIBC_StatusCode status = self._this.find_max_range(
            low_angle_deg,
            high_angle_deg,
            _APEX_IS_MAX_RANGE_RADIANS,
            &result
        )

        if status == BCLIBC_StatusCode.SUCCESS:
            return result

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        self._raise_solver_runtime_error(err)

    cdef BCLIBC_BaseTrajData _find_apex(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
    ):
        """
        Internal implementation to find the apex of the trajectory.

        Returns:
            BCLIBC_BaseTrajData: The trajectory data at the apex.
        """
        self._init_trajectory(shot_info)
        cdef BCLIBC_BaseTrajData apex = BCLIBC_BaseTrajData()
        cdef BCLIBC_StatusCode status = self._this.find_apex(&apex)

        if status == BCLIBC_StatusCode.SUCCESS:
            return apex

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        self._raise_solver_runtime_error(err)

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
        cdef:
            double result
            BCLIBC_OutOfRangeError range_error = {}
            BCLIBC_ZeroFindingError zero_error = {}
        cdef BCLIBC_StatusCode status = self._this.zero_angle(
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            &result,
            &range_error,
            &zero_error,
        )

        if status == BCLIBC_StatusCode.SUCCESS:
            return result

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        if err.src == BCLIBC_ErrorSource.INIT_ZERO:
            self._raise_on_init_zero_error(err, &range_error)
        if err.src == BCLIBC_ErrorSource.ZERO_ANGLE:
            self._raise_on_init_zero_error(err, &range_error)
            self._raise_on_zero_finding_error(err, &zero_error)
        self._raise_solver_runtime_error(err)

    cdef tuple _integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
    ):
        """
        Internal method to perform trajectory integration.

        Args:
            range_limit_ft (double): Maximum range limit in feet.
            range_step_ft (double): Range step in feet.
            time_step (double): Time step in seconds.
            filter_flags (BCLIBC_TrajFlag): Flags to filter trajectory data.

        Returns:
            tuple: (BaseTrajSeqT, str or None)
                BaseTrajSeqT: The trajectory sequence.
                BCLIBC_TerminationReason: Termination reason if applicable.
        """
        self._init_trajectory(shot_info)
        cdef:
            BaseTrajSeqT trajectory = BaseTrajSeqT()
            BCLIBC_TerminationReason reason
        cdef BCLIBC_StatusCode status = self._this.integrate_dense(
            range_limit_ft,
            range_step_ft,
            time_step,
            &trajectory._this,
            &reason,
        )

        if status == BCLIBC_StatusCode.SUCCESS:
            return trajectory, reason

        cdef const BCLIBC_ErrorFrame *err = BCLIBC_ErrorStack_lastErr(&self._this.err_stack)
        self._raise_solver_runtime_error(err)

    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *err,
        const BCLIBC_OutOfRangeError *err_data
    ):
        if err.code == BCLIBC_ErrorType.OUT_OF_RANGE_ERROR:
            raise OutOfRangeError(
                feet_from_c(err_data.requested_distance_ft),
                feet_from_c(err_data.max_range_ft),
                rad_from_c(err_data.look_angle_rad)
            )

    cdef void _raise_on_zero_finding_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *err,
        const BCLIBC_ZeroFindingError *zero_error
    ):
        cdef const char* c_msg
        cdef object error_message

        if err.code == BCLIBC_ErrorType.ZERO_FINDING_ERROR:
            c_msg = <const char*>err.msg
            error_message = c_msg.decode('utf-8', 'replace') if c_msg is not NULL else "C-level error message was NULL"
            raise ZeroFindingError(
                zero_error.zero_finding_error,
                zero_error.iterations_count,
                rad_from_c(zero_error.last_barrel_elevation_rad),
                error_message
            )

    cdef void _raise_solver_runtime_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *f
    ):
        cdef const BCLIBC_ErrorStack *stack = &self._this.err_stack
        if stack.top <= 0 or f.code == BCLIBC_ErrorType.NO_ERROR:
            return

        cdef char trace[4096]
        BCLIBC_ErrorStack_toString(stack, trace, sizeof(trace))

        cdef str trace_str = trace.decode('utf-8', 'ignore')
        cdef list lines = [
            ("=> " if i==len(trace_str.splitlines())-1 else "   ") + line
            for i, line in enumerate(trace_str.splitlines()) if line
        ]

        trace_str = "Trace:\n" + "\n".join(lines)

        cdef object exception_type = ERROR_TYPE_TO_EXCEPTION.get(f.code, RuntimeError)
        raise exception_type(trace_str)


cdef list TrajectoryData_list_from_cpp(const vector[BCLIBC_TrajectoryData] *records):
    cdef list py_list = []
    cdef vector[BCLIBC_TrajectoryData].const_iterator it = records.begin()
    cdef vector[BCLIBC_TrajectoryData].const_iterator end = records.end()

    while it != end:
        py_list.append(TrajectoryData_from_cpp(deref(it)))
        inc(it)

    return py_list


cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data):
    cdef object pydata = TrajectoryData(
        time=cpp_data.time,
        distance=TrajectoryData._new_feet(cpp_data.distance_ft),
        velocity=TrajectoryData._new_fps(cpp_data.velocity_fps),
        mach=cpp_data.mach,
        height=TrajectoryData._new_feet(cpp_data.height_ft),
        slant_height=TrajectoryData._new_feet(cpp_data.slant_height_ft),
        drop_angle=TrajectoryData._new_rad(cpp_data.drop_angle_rad),
        windage=TrajectoryData._new_feet(cpp_data.windage_ft),
        windage_angle=TrajectoryData._new_rad(cpp_data.windage_angle_rad),
        slant_distance=TrajectoryData._new_feet(cpp_data.slant_distance_ft),
        angle=TrajectoryData._new_rad(cpp_data.angle_rad),
        density_ratio=cpp_data.density_ratio,
        drag=cpp_data.drag,
        energy=TrajectoryData._new_ft_lb(cpp_data.energy_ft_lb),
        ogw=TrajectoryData._new_lb(cpp_data.ogw_lb),
        flag=cpp_data.flag
    )
    return pydata
