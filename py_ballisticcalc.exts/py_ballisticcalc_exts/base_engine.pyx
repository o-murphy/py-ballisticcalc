# cython: freethreading_compatible=True
"""
CythonizedBaseIntegrationEngine

Presently ._integrate() returns dense data in a BaseTrajSeqT, then .integrate()
    feeds it through the Python TrajectoryDataFilter to build List[TrajectoryData].
TODO: Implement a Cython TrajectoryDataFilter for increased speed?
"""
# (Avoid importing cpython.exc; raise Python exceptions directly in cdef functions where needed)
# noinspection PyUnresolvedReferences
from libc.math cimport sin, cos
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport (
    BaseTrajSeqT,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT, BaseTrajData_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    # types and methods
    Atmosphere_t,
    ShotProps_t,
    ShotProps_t_updateStabilityCoefficient,
    TrajFlag_t,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bind cimport (
    # factory funcs
    Config_t_from_pyobject,
    MachList_t_from_pylist,
    Curve_t_from_pylist,
    Coriolis_t_from_pyobject,
    WindSock_t_from_pylist,
    _new_feet,
    _new_rad,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.error_stack cimport (
    StatusCode,
    ErrorSource,
    ErrorFrame,
    ErrorType,
    last_err,
    error_stack_to_string,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.log cimport initLogLevel

from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.conditions import Coriolis
from py_ballisticcalc.engines.base_engine import create_base_engine_config, TrajectoryDataFilter
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine as _PyBaseIntegrationEngine
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.trajectory_data import HitResult, BaseTrajData, TrajectoryData
from py_ballisticcalc.unit import Angular

__all__ = (
    'CythonizedBaseIntegrationEngine',
)


# force initLogLevel
initLogLevel()


cdef double _ALLOWED_ZERO_ERROR_FEET = _PyBaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET
cdef double _APEX_IS_MAX_RANGE_RADIANS = _PyBaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS


cdef dict ERROR_TYPE_TO_EXCEPTION = {
    ErrorType.T_INPUT_ERROR: TypeError,
    ErrorType.T_ZERO_FINDING_ERROR: ZeroFindingError,
    ErrorType.T_OUT_OF_RANGE_ERROR: OutOfRangeError,
    ErrorType.T_VALUE_ERROR: ValueError,
    ErrorType.T_INDEX_ERROR: IndexError,
    ErrorType.T_KEY_ERROR: AttributeError,
    ErrorType.T_MEMORY_ERROR: MemoryError,
    ErrorType.T_ARITHMETIC_ERROR: ArithmeticError,
    ErrorType.T_RUNTIME_ERROR: SolverRuntimeError,
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
            The Engine_t is built-in to CythonizedBaseIntegrationEngine,
            so we are need no set it's fields to null
        """
        # self._engine.gravity_vector = V3dT(.0, .0, .0)
        # self._engine.integration_step_count = 0
        pass

    def __dealloc__(CythonizedBaseIntegrationEngine self):
        """Frees any allocated resources."""
        Engine_t_release_trajectory(&self._engine)

    @property
    def integration_step_count(self) -> int:
        """
        Gets the number of integration steps performed in the last integration.

        Returns:
            int: The number of integration steps.
        """
        return self._engine.integration_step_count

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self):
        """Gets the calculation step size in feet."""
        return self._engine.config.cStepMultiplier

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
        self._init_trajectory(shot_info)
        cdef MaxRangeResult_t res
        try:
            res = self._find_max_range(
                angle_bracket_deg[0], angle_bracket_deg[1]
            )
            return _new_feet(res.max_range_ft), _new_rad(res.angle_at_max_rad)
        finally:
            self._release_trajectory()

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
        self._init_trajectory(shot_info)
        cdef double zero_angle
        try:
            zero_angle = self._find_zero_angle(distance._feet, lofted)
            return _new_rad(zero_angle)
        finally:
            self._release_trajectory()

    def find_apex(self, object shot_info) -> TrajectoryData:
        """
        Finds the apex of the trajectory, where apex is defined as the point
        where the vertical component of velocity goes from positive to negative.

        Args:
            shot_info (Shot): The shot information.

        Returns:
            TrajectoryData: The trajectory data at the apex.
        """
        self._init_trajectory(shot_info)
        cdef BaseTrajDataT result
        cdef object props
        try:
            result = BaseTrajDataT(self._find_apex())
            props = ShotProps.from_shot(shot_info)
            return TrajectoryData.from_props(
                props, result.time, result.position, result.velocity, result.mach)
        finally:
            self._release_trajectory()

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
            StatusCode status
            double result
            OutOfRangeError_t range_error
            ZeroFindingError_t zero_error
            ErrorFrame *err

        try:
            status = Engine_t_zero_angle_with_fallback(
                &self._engine,
                distance._feet,
                _APEX_IS_MAX_RANGE_RADIANS,
                _ALLOWED_ZERO_ERROR_FEET,
                &result,
                &range_error,
                &zero_error,
            )

            if status == StatusCode.STATUS_SUCCESS:
                return _new_rad(result)

            err = last_err(&self._engine.err_stack)

            if err.src == ErrorSource.SRC_INIT_ZERO:
                self._raise_on_init_zero_error(err, &range_error)
            if err.src == ErrorSource.SRC_FIND_ZERO_ANGLE:
                self._raise_on_init_zero_error(err, &range_error)
                self._raise_on_zero_finding_error(err, &zero_error)
            self._raise_solver_runtime_error(err)

        finally:
            self._release_trajectory()

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
            TerminationReason reason
            StatusCode status
            BaseTrajSeqT trajectory
            BaseTrajDataT init, fin
            double range_limit_ft = max_range._feet
            double range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft
            object props, tdf
            object termination_reason = None

        self._init_trajectory(shot_info)
        cdef ErrorFrame *err

        try:
            trajectory = BaseTrajSeqT()
            status = Engine_t_integrate(
                &self._engine,
                range_limit_ft,
                range_step_ft,
                time_step,
                <TrajFlag_t>filter_flags,
                &trajectory._c_view,
                &reason,
            )

            if status == StatusCode.STATUS_ERROR:
                err = last_err(&self._engine.err_stack)
                self._raise_solver_runtime_error(err)
        finally:
            # Always release C resources
            self._release_trajectory()

        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()  # Add missing calc_step attribute

        # Extract termination_reason from the result
        if reason == TerminationReason.RANGE_ERROR_MINIMUM_VELOCITY_REACHED:
            termination_reason = RangeError.MinimumVelocityReached
        elif reason == TerminationReason.RANGE_ERROR_MAXIMUM_DROP_REACHED:
            termination_reason = RangeError.MaximumDropReached
        elif reason == TerminationReason.RANGE_ERROR_MINIMUM_ALTITUDE_REACHED:
            termination_reason = RangeError.MinimumAltitudeReached

        init = trajectory[0]
        tdf = TrajectoryDataFilter(props, filter_flags, init.position, init.velocity,
                                   props.barrel_elevation_rad, props.look_angle_rad,
                                   range_limit_ft, range_step_ft, time_step)

        # Feed step_data through TrajectoryDataFilter to get TrajectoryData
        for _, d in enumerate(trajectory):
            tdf.record(BaseTrajData(d.time, d.position, d.velocity, d.mach))
        if termination_reason is not None:
            termination_reason = RangeError(termination_reason, tdf.records)
            # For incomplete trajectories we add last point, so long as it isn't a duplicate
            fin = trajectory[-1]
            if fin.time > tdf.records[-1].time:
                tdf.records.append(TrajectoryData.from_props(
                    props,
                    fin.time, fin.position, fin.velocity, fin.mach,
                    TrajFlag_t.TFLAG_NONE
                ))
        return HitResult(
            props,
            tdf.records,
            trajectory if dense_output else None,
            filter_flags != TrajFlag_t.TFLAG_NONE,
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
        cdef:
            double out_error_ft

        cdef StatusCode status = Engine_t_error_at_distance(
            &self._engine,
            angle_rad,
            target_x_ft,
            target_y_ft,
            &out_error_ft
        )

        if status == StatusCode.STATUS_SUCCESS:
            return out_error_ft

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        self._raise_solver_runtime_error(err)

    cdef void _release_trajectory(CythonizedBaseIntegrationEngine self):
        """
        Releases the resources held by the trajectory.
        """
        Engine_t_release_trajectory(&self._engine)

    cdef ShotProps_t* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    ):
        """
        Converts Shot properties into floats dimensioned in internal units.

        Args:
            shot_info (Shot): Information about the shot.

        Returns:
            ShotProps_t*: Pointer to the initialized shot properties.
        """

        # --- 🛑 CRITICAL FIX: FREE OLD RESOURCES FIRST ---
        self._release_trajectory()
        # ---------------------------------------------------

        # hack to reload config if it was changed explicit on existed instance
        self._engine.config = Config_t_from_pyobject(self._config)
        self._engine.gravity_vector = V3dT(.0, self._engine.config.cGravityConstant, .0)

        self._table_data = shot_info.ammo.dm.drag_table
        # Build C shot struct with robust cleanup on any error that follows

        # WARNING: Avoid calling Python attributes in a chain!
        # Cython may forget to add DECREF, so memory leaks are possible
        cdef object velocity_obj = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp)
        cdef double muzzle_velocity_fps = velocity_obj._fps

        # Create coriolis object from shot parameters
        cdef object coriolis_obj = Coriolis.create(
            shot_info.latitude,
            shot_info.azimuth,
            muzzle_velocity_fps
        )

        try:
            self._engine.shot = ShotProps_t(
                bc=shot_info.ammo.dm.BC,
                look_angle=shot_info.look_angle._rad,
                twist=shot_info.weapon.twist._inch,
                length=shot_info.ammo.dm.length._inch,
                diameter=shot_info.ammo.dm.diameter._inch,
                weight=shot_info.ammo.dm.weight._grain,
                barrel_elevation=shot_info.barrel_elevation._rad,
                barrel_azimuth=shot_info.barrel_azimuth._rad,
                sight_height=shot_info.weapon.sight_height._feet,
                cant_cosine=cos(shot_info.cant_angle._rad),
                cant_sine=sin(shot_info.cant_angle._rad),
                alt0=shot_info.atmo.altitude._feet,
                calc_step=self.get_calc_step(),
                muzzle_velocity=muzzle_velocity_fps,
                stability_coefficient=0.0,
                curve=Curve_t_from_pylist(self._table_data),
                mach_list=MachList_t_from_pylist(self._table_data),
                atmo=Atmosphere_t(
                    _t0=shot_info.atmo._t0,
                    _a0=shot_info.atmo._a0,
                    _p0=shot_info.atmo._p0,
                    _mach=shot_info.atmo._mach,
                    density_ratio=shot_info.atmo.density_ratio,
                    cLowestTempC=shot_info.atmo.cLowestTempC,
                ),
                coriolis=Coriolis_t_from_pyobject(coriolis_obj),
                wind_sock=WindSock_t_from_pylist(shot_info.winds),
                filter_flags=TrajFlag_t.TFLAG_NONE,
            )

            # Assume can return only ZERO_DIVISION_ERROR or NO_ERROR
            if ShotProps_t_updateStabilityCoefficient(&self._engine.shot) != <int>ErrorType.T_NO_ERROR:
                raise ZeroDivisionError(
                    "Zero division detected in ShotProps_t_updateStabilityCoefficient")

        except Exception:
            # Ensure we free any partially allocated arrays inside _shot_s
            self._release_trajectory()
            raise

        return &self._engine.shot

    cdef StatusCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        ZeroInitialData_t *out,
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

        cdef OutOfRangeError_t err_data
        cdef StatusCode status = Engine_t_init_zero_calculation(
            &self._engine,
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            out,
            &err_data,
        )
        if status == StatusCode.STATUS_SUCCESS:
            return status

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        if err.src == ErrorSource.SRC_INIT_ZERO:
            self._raise_on_init_zero_error(err, &err_data)
        self._raise_solver_runtime_error(err)

    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
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

        cdef OutOfRangeError_t range_error
        cdef ZeroFindingError_t zero_error
        cdef double result
        cdef StatusCode status = Engine_t_find_zero_angle(
            &self._engine,
            distance,
            lofted,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            &result,
            &range_error,
            &zero_error,
        )
        if status == StatusCode.STATUS_SUCCESS:
            return result

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)

        if err.src == ErrorSource.SRC_INIT_ZERO:
            self._raise_on_init_zero_error(err, &range_error)
        if err.src == ErrorSource.SRC_FIND_ZERO_ANGLE:
            self._raise_on_init_zero_error(err, &range_error)
            self._raise_on_zero_finding_error(err, &zero_error)
        self._raise_solver_runtime_error(err)

    cdef MaxRangeResult_t _find_max_range(
        CythonizedBaseIntegrationEngine self,
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

        cdef MaxRangeResult_t result
        cdef StatusCode status = Engine_t_find_max_range(
            &self._engine,
            low_angle_deg,
            high_angle_deg,
            _APEX_IS_MAX_RANGE_RADIANS,
            &result
        )

        if status == StatusCode.STATUS_SUCCESS:
            return result

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        self._raise_solver_runtime_error(err)

    cdef BaseTrajData_t _find_apex(
        CythonizedBaseIntegrationEngine self,
    ):
        """
        Internal implementation to find the apex of the trajectory.

        Returns:
            BaseTrajData_t: The trajectory data at the apex.
        """

        cdef BaseTrajData_t apex

        # FIXME: possibly needs to be initialised with zeros
        # apex = BaseTrajData_t(
        #     0.0, V3dT(0.0, 0.0, 0.0), V3dT(0.0, 0.0, 0.0), 0.0)

        cdef StatusCode status = Engine_t_find_apex(&self._engine, &apex)
        if status == StatusCode.STATUS_SUCCESS:
            return apex

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        self._raise_solver_runtime_error(err)

    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        double distance
    ):
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            props (ShotProps_t): Shot parameters
            distance (double): Sight distance to zero (i.e., along Shot.look_angle), units=feet,
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """

        cdef:
            double result
            OutOfRangeError_t range_error
            ZeroFindingError_t zero_error

        cdef StatusCode status = Engine_t_zero_angle(
            &self._engine,
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            &result,
            &range_error,
            &zero_error,
        )

        if status == StatusCode.STATUS_SUCCESS:
            return result

        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        if err.src == ErrorSource.SRC_INIT_ZERO:
            self._raise_on_init_zero_error(err, &range_error)
        if err.src == ErrorSource.SRC_ZERO_ANGLE:
            self._raise_on_init_zero_error(err, &range_error)
            self._raise_on_zero_finding_error(err, &zero_error)
        self._raise_solver_runtime_error(err)

    cdef tuple _integrate(
        CythonizedBaseIntegrationEngine self,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
    ):
        """
        Internal method to perform trajectory integration.

        Args:
            range_limit_ft (double): Maximum range limit in feet.
            range_step_ft (double): Range step in feet.
            time_step (double): Time step in seconds.
            filter_flags (TrajFlag_t): Flags to filter trajectory data.

        Returns:
            tuple: (BaseTrajSeqT, str or None)
                BaseTrajSeqT: The trajectory sequence.
                TerminationReason: Termination reason if applicable.
        """
        if self._engine.integrate_func_ptr is NULL:
            raise NotImplementedError("integrate_func not implemented or not provided")

        cdef:
            BaseTrajSeqT traj_seq = BaseTrajSeqT()
            TerminationReason reason

        cdef StatusCode status = Engine_t_integrate(
            &self._engine,
            range_limit_ft,
            range_step_ft,
            time_step,
            filter_flags,
            &traj_seq._c_view,
            &reason,
        )

        if status == StatusCode.STATUS_SUCCESS:
            return traj_seq, reason
        cdef ErrorFrame *err = last_err(&self._engine.err_stack)
        self._raise_solver_runtime_error(err)

    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        ErrorFrame *err,
        OutOfRangeError_t *err_data
    ):
        if err.code == ErrorType.T_OUT_OF_RANGE_ERROR:
            raise OutOfRangeError(
                _new_feet(err_data.requested_distance_ft),
                _new_feet(err_data.max_range_ft),
                _new_rad(err_data.look_angle_rad)
            )

    cdef void _raise_on_zero_finding_error(
        CythonizedBaseIntegrationEngine self,
        ErrorFrame *err,
        ZeroFindingError_t *zero_error
    ):
        if err.code == ErrorType.T_ZERO_FINDING_ERROR:
            raise ZeroFindingError(
                zero_error.zero_finding_error,
                zero_error.iterations_count,
                _new_rad(zero_error.last_barrel_elevation_rad),
                err.msg.decode('utf-8')
            )

    cdef void _raise_solver_runtime_error(CythonizedBaseIntegrationEngine self, ErrorFrame *f):
        cdef ErrorStack *stack = &self._engine.err_stack
        if stack.top <= 0 or f.code == ErrorType.T_NO_ERROR:
            return

        # Отримуємо exception, дефолт – RuntimeError
        cdef object exception_type = ERROR_TYPE_TO_EXCEPTION.get(f.code, RuntimeError)

        cdef char trace[4096]
        error_stack_to_string(stack, trace, sizeof(trace))

        cdef str trace_str = trace.decode('utf-8', 'ignore')
        cdef list lines = [
            ("=> " if i==len(trace_str.splitlines())-1 else "   ") + line
            for i, line in enumerate(trace_str.splitlines()) if line
        ]

        trace_str = "Trace:\n" + "\n".join(lines)

        raise exception_type(trace_str)
