# cython: freethreading_compatible=True
"""
CythonizedBaseIntegrationEngine

Presently ._integrate() returns dense data in a BaseTrajSeqT, then .integrate()
    feeds it through the Python TrajectoryDataFilter to build List[TrajectoryData].
TODO: Implement a Cython TrajectoryDataFilter for increased speed?
"""
# (Avoid importing cpython.exc; raise Python exceptions directly in cdef functions where needed)
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan2, sqrt, copysign
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport (
    BaseTrajSeqT,
    BaseTraj_t,
    InterpKey,
    BaseTrajSeq_t_get_raw_item,
    BaseTrajSeq_t_get_at,
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
    ErrorCode,
    initLogLevel,
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


initLogLevel()

cdef double _ALLOWED_ZERO_ERROR_FEET = _PyBaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET
cdef double _APEX_IS_MAX_RANGE_RADIANS = _PyBaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS


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

    @property
    def error_message(self) -> str:
        """
        Gets the last error message from the engine.

        Returns:
            str: The error message.
        """
        return self.get_error_message()

    cdef str get_error_message(CythonizedBaseIntegrationEngine self):
        """
        Gets the last error message from the engine.

        Returns:
            str: The error message.
        """
        # Get length up to first null terminator
        cdef Py_ssize_t n = strlen(self._engine.err_msg)
        return self._engine.err_msg[:n].decode('utf-8', 'ignore')

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
        cdef ShotProps_t* shot_props_ptr = self._init_trajectory(shot_info)
        cdef MaxRangeResult_t res
        try:
            res = self._find_max_range(
                shot_props_ptr, angle_bracket_deg[0], angle_bracket_deg[1]
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
        cdef ShotProps_t* shot_props_ptr = self._init_trajectory(shot_info)
        cdef double zero_angle
        try:
            zero_angle = self._find_zero_angle(shot_props_ptr, distance._feet, lofted)
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
        cdef ShotProps_t* shot_props_ptr = self._init_trajectory(shot_info)
        cdef double zero_angle
        try:
            zero_angle = self._zero_angle(shot_props_ptr, distance._feet)
            return _new_rad(zero_angle)
        except ZeroFindingError:
            # Fallback to guaranteed method
            shot_props_ptr = self._init_trajectory(shot_info)
            zero_angle = self._find_zero_angle(shot_props_ptr, distance._feet, False)
            return _new_rad(zero_angle)
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
            tuple _res
            object props, error, tdf
            BaseTrajSeqT trajectory
            BaseTrajDataT init, fin
            double range_limit_ft = max_range._feet
            double range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft

        self._init_trajectory(shot_info)

        try:
            _res = self._integrate(range_limit_ft, range_step_ft, time_step, <TrajFlag_t>filter_flags)
        finally:
            # Always release C resources
            self._release_trajectory()
        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()  # Add missing calc_step attribute

        # Extract trajectory and step_data from the result
        trajectory = _res[0]
        error = _res[1]
        init = trajectory[0]
        tdf = TrajectoryDataFilter(props, filter_flags, init.position, init.velocity,
                                   props.barrel_elevation_rad, props.look_angle_rad,
                                   range_limit_ft, range_step_ft, time_step)

        # Feed step_data through TrajectoryDataFilter to get TrajectoryData
        for _, d in enumerate(trajectory):
            tdf.record(BaseTrajData(d.time, d.position, d.velocity, d.mach))
        if error is not None:
            error = RangeError(error, tdf.records)
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
            error
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
            shot_props_ptr (ShotProps_t*): Pointer to shot properties.
            angle_rad (double): Launch angle in radians.
            target_x_ft (double): Target X coordinate in feet.
            target_y_ft (double): Target Y coordinate in feet.

        Returns:
            double: The miss distance in feet (positive if overshot, negative if undershot).
        """
        cdef:
            ErrorCode err
            double out_error_ft

        err = Engine_t_error_at_distance(
            &self._engine,
            angle_rad,
            target_x_ft,
            target_y_ft,
            &out_error_ft
        )

        self._raise_on_input_error(err)

        if err == ErrorCode.NO_ERROR or isRangeError(err):
            return out_error_ft

        if err == ErrorCode.VALUE_ERROR:
            raise ValueError(self.error_message)

        raise SolverRuntimeError(
            f"Failed to integrate trajectory for error_at_distance, "
            f"error code: {err}, {self.error_message}"
        )

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
            if ShotProps_t_updateStabilityCoefficient(&self._engine.shot) < 0:
                raise ZeroDivisionError("Zero division detected in ShotProps_t_updateStabilityCoefficient")

        except Exception:
            # Ensure we free any partially allocated arrays inside _shot_s
            self._release_trajectory()
            raise

        return &self._engine.shot

    cdef ErrorCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        ZeroInitialData_t *out,
    ):
        """
        Initializes the zero calculation for the given shot and distance.
        Handles edge cases.

        Args:
            shot_props_ptr (const ShotProps_t*): Pointer to shot properties.
            distance (double): The distance to the target in feet.

        Returns:
            tuple: (status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
            where status is: 0 = CONTINUE, 1 = DONE (early return with look_angle_rad)
        """

        cdef OutOfRangeError_t err_data
        cdef ErrorCode err = Engine_t_init_zero_calculation(
            &self._engine,
            distance,
            _APEX_IS_MAX_RANGE_RADIANS,
            _ALLOWED_ZERO_ERROR_FEET,
            out,
            &err_data,
        )
        self._raise_on_input_error(err)
        self._raise_on_init_zero_error(err, &err_data)
        return err

    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
        double distance,
        bint lofted
    ):
        """
        Find zero angle using Ridder's method for guaranteed convergence.

        Args:
            shot_props_ptr (ShotProps_t*): Pointer to shot properties.
            distance (double): The distance to the target in feet.
            lofted (bint): Whether the shot is lofted.

        Returns:
            double: The calculated zero angle in radians.
        """
        # Get initialization data
        cdef ZeroInitialData_t init_data
        cdef ErrorCode status = self._init_zero_calculation(distance, &init_data)
        cdef:
            double look_angle_rad = init_data.look_angle_rad
            double slant_range_ft = init_data.slant_range_ft
            double target_x_ft = init_data.target_x_ft
            double target_y_ft = init_data.target_y_ft
            double start_height_ft = init_data.start_height_ft

        if status == ErrorCode.ZERO_INIT_DONE:  # DONE
            return look_angle_rad

        # 1. Find the maximum possible range to establish a search bracket.
        cdef MaxRangeResult_t max_range_result = self._find_max_range(
            shot_props_ptr, 0, 90
        )
        cdef double max_range_ft = max_range_result.max_range_ft
        cdef double angle_at_max_rad = max_range_result.angle_at_max_rad

        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(_new_feet(distance), _new_feet(max_range_ft), _new_rad(look_angle_rad))
        if fabs(slant_range_ft - max_range_ft) < _ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max_rad

        # Backup and adjust constraints (emulate @with_no_minimum_velocity)
        cdef double restore_cMinimumVelocity__zero = 0.0
        cdef int has_restore_cMinimumVelocity__zero = 0
        if self._engine.config.cMinimumVelocity != <double>0.0:
            restore_cMinimumVelocity__zero = self._engine.config.cMinimumVelocity
            self._engine.config.cMinimumVelocity = 0.0
            has_restore_cMinimumVelocity__zero = 1

        # 3. Establish search bracket for the zero angle.
        cdef:
            double low_angle, high_angle
            double sight_height_adjust = 0.0
            double f_low, f_high

        if lofted:
            low_angle = angle_at_max_rad
            high_angle = 1.5690308719637473  # 89.9 degrees in radians
        else:
            if start_height_ft > 0:
                sight_height_adjust = atan2(start_height_ft, target_x_ft)
            low_angle = look_angle_rad - sight_height_adjust
            high_angle = angle_at_max_rad

        cdef str reason

        # Prepare variables for Ridder's method outside of try block to satisfy Cython
        cdef int iteration
        cdef double mid_angle, f_mid, s, next_angle, f_next

        try:
            f_low = self._error_at_distance(low_angle, target_x_ft, target_y_ft)
            # If low is exactly look angle and failed to evaluate, nudge slightly upward to bracket
            if f_low > <double>1e8 and fabs(low_angle - look_angle_rad) < <double>1e-9:
                low_angle = look_angle_rad + 1e-3
                f_low = self._error_at_distance(low_angle, target_x_ft, target_y_ft)
            f_high = self._error_at_distance(high_angle, target_x_ft, target_y_ft)

            if f_low * f_high >= 0:
                lofted_str = "lofted" if lofted else "low"
                reason = (
                    f"No {lofted_str} zero trajectory in elevation range "
                    f"({low_angle * 57.29577951308232:.2f}, "
                    f"{high_angle * 57.29577951308232:.2f} deg). "
                    f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
                )
                raise ZeroFindingError(
                    float(target_y_ft),
                    0,
                    _new_rad(shot_props_ptr.barrel_elevation),
                    reason=reason
                )

            # 4. Ridder's method implementation
            for iteration in range(self._engine.config.cMaxIterations):
                mid_angle = (low_angle + high_angle) / 2.0
                f_mid = self._error_at_distance(mid_angle, target_x_ft, target_y_ft)

                # s is the updated point using the root of the linear function
                # through (low_angle, f_low) and (high_angle, f_high)
                # and the quadratic function that passes through those points and (mid_angle, f_mid)
                s = sqrt(f_mid * f_mid - f_low * f_high)
                if s == 0.0:
                    break  # Should not happen if f_low and f_high have opposite signs

                next_angle = mid_angle + (mid_angle - low_angle) * (copysign(1.0, f_low - f_high) * f_mid / s)
                if fabs(next_angle - mid_angle) < self._engine.config.cZeroFindingAccuracy:
                    return next_angle

                f_next = self._error_at_distance(next_angle, target_x_ft, target_y_ft)
                # Update the bracket
                if f_mid * f_next < 0:
                    low_angle, f_low = mid_angle, f_mid
                    high_angle, f_high = next_angle, f_next
                elif f_low * f_next < 0:
                    high_angle, f_high = next_angle, f_next
                elif f_high * f_next < 0:
                    low_angle, f_low = next_angle, f_next
                else:
                    break  # If we are here, something is wrong, the root is not bracketed anymore

                if fabs(high_angle - low_angle) < self._engine.config.cZeroFindingAccuracy:
                    return (low_angle + high_angle) / 2

            raise ZeroFindingError(
                target_y_ft,
                self._engine.config.cMaxIterations,
                _new_rad((low_angle + high_angle) / 2),
                reason="Ridder's method failed to converge."
            )
        finally:
            if has_restore_cMinimumVelocity__zero:
                self._engine.config.cMinimumVelocity = restore_cMinimumVelocity__zero

    cdef MaxRangeResult_t _find_max_range(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
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
        cdef:
            double look_angle_rad = shot_props_ptr.look_angle
            double max_range_ft
            double angle_at_max_rad
            BaseTrajData_t _apex_obj
            double _sdist

        # Virtually vertical shot
        if (
            fabs(look_angle_rad - <double>1.5707963267948966) < _APEX_IS_MAX_RANGE_RADIANS
        ):  # π/2 radians = 90 degrees
            _apex_obj = self._find_apex()
            _sdist = (
                _apex_obj.position.x
                * cos(look_angle_rad)
                + _apex_obj.position.y
                * sin(look_angle_rad)
            )
            return MaxRangeResult_t(_sdist, look_angle_rad)

        # Backup and adjust constraints (emulate @with_max_drop_zero and @with_no_minimum_velocity)
        cdef:
            double restore_cMaximumDrop = 0.0
            int has_restore_cMaximumDrop = 0
            double restore_cMinimumVelocity = 0.0
            int has_restore_cMinimumVelocity = 0

        if self._engine.config.cMaximumDrop != <double>0.0:
            restore_cMaximumDrop = self._engine.config.cMaximumDrop
            self._engine.config.cMaximumDrop = 0.0  # We want to run trajectory until it returns to horizontal
            has_restore_cMaximumDrop = 1
        if self._engine.config.cMinimumVelocity != <double>0.0:
            restore_cMinimumVelocity = self._engine.config.cMinimumVelocity
            self._engine.config.cMinimumVelocity = 0.0
            has_restore_cMinimumVelocity = 1

        cdef:
            double inv_phi = 0.6180339887498949  # (sqrt(5) - 1) / 2
            double inv_phi_sq = 0.38196601125010515  # inv_phi^2
            double a = low_angle_deg * 0.017453292519943295  # Convert to radians
            double b = high_angle_deg * 0.017453292519943295  # Convert to radians
            double h = b - a
            double c = a + inv_phi_sq * h
            double d = a + inv_phi * h
            double yc, yd
            int iteration

        def range_for_angle(angle_rad):
            """Returns max slant-distance for given launch angle in radians.
            Robust ZERO_DOWN detection: scan from the end and find the first slant-height
            crossing where the previous point is positive and current is non-positive."""
            cdef double ca
            cdef double sa
            cdef double h_prev
            cdef double h_cur
            cdef double denom
            cdef double t
            cdef double ix
            cdef double iy
            cdef double sdist
            cdef BaseTrajSeqT trajectory
            cdef Py_ssize_t n
            cdef Py_ssize_t i
            cdef BaseTraj_t* prev_ptr
            cdef BaseTraj_t* cur_ptr
            # Update shot data
            shot_props_ptr.barrel_elevation = angle_rad
            try:
                _res = self._integrate(9e9, 9e9, 0.0, TrajFlag_t.TFLAG_NONE)
                trajectory = <BaseTrajSeqT>_res[0]
                ca = cos(shot_props_ptr.look_angle)
                sa = sin(shot_props_ptr.look_angle)
                n = trajectory._c_view.length
                if n >= 2:
                    # Linear search from end of trajectory for zero-down crossing
                    for i in range(n - 1, 0, -1):
                        prev_ptr = BaseTrajSeq_t_get_raw_item(
                            &trajectory._c_view, i - 1
                        )
                        if prev_ptr is NULL:
                            return -9e9  # assume IndexError
                        cur_ptr = BaseTrajSeq_t_get_raw_item(
                            &trajectory._c_view, i
                        )
                        if cur_ptr is NULL:
                            return -9e9  # assume IndexError
                        h_prev = prev_ptr.py * ca - prev_ptr.px * sa
                        h_cur = cur_ptr.py * ca - cur_ptr.px * sa
                        if h_prev > 0.0 and h_cur <= 0.0:
                            # Interpolate for slant_distance
                            denom = h_prev - h_cur
                            if denom == 0.0:
                                t = 0.0
                            else:
                                t = h_prev / denom
                            if t < 0.0:
                                t = 0.0
                            elif t > 1.0:
                                t = 1.0
                            ix = prev_ptr.px + t * (cur_ptr.px - prev_ptr.px)
                            iy = prev_ptr.py + t * (cur_ptr.py - prev_ptr.py)
                            sdist = ix * ca + iy * sa
                            return sdist
                return -9e9
            except RangeError:
                return -9e9

        yc = range_for_angle(c)
        yd = range_for_angle(d)

        # Golden-section search
        for iteration in range(100):  # 100 iterations is more than enough for high precision
            if h < <double>1e-5:  # Angle tolerance in radians
                break
            if yc > yd:
                b, d, yd = d, c, yc
                h = b - a
                c = a + inv_phi_sq * h
                yc = range_for_angle(c)
            else:
                a, c, yc = c, d, yd
                h = b - a
                d = a + inv_phi * h
                yd = range_for_angle(d)

        angle_at_max_rad = (a + b) / 2
        max_range_ft = range_for_angle(angle_at_max_rad)

        # Restore original constraints
        if has_restore_cMaximumDrop:
            self._engine.config.cMaximumDrop = restore_cMaximumDrop
        if has_restore_cMinimumVelocity:
            self._engine.config.cMinimumVelocity = restore_cMinimumVelocity

        return MaxRangeResult_t(max_range_ft, angle_at_max_rad)

    cdef BaseTrajData_t _find_apex(
        CythonizedBaseIntegrationEngine self,
    ):
        """
        Internal implementation to find the apex of the trajectory.

        Args:
            shot_props_ptr (const ShotProps_t*): Pointer to shot properties.

        Returns:
            BaseTrajData_t: The trajectory data at the apex.
        """

        cdef BaseTrajData_t apex

        # FIXME: possibly needs to be initialised with zeros
        # apex = BaseTrajData_t(
        #     0.0, V3dT(0.0, 0.0, 0.0), V3dT(0.0, 0.0, 0.0), 0.0)

        cdef ErrorCode err = Engine_t_find_apex(&self._engine, &apex)
        self._raise_on_input_error(err)
        self._raise_on_apex_error(err)
        return apex

    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
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
        # Get initialization data using the new method
        cdef ZeroInitialData_t init_data
        cdef ErrorCode status = self._init_zero_calculation(distance, &init_data)
        cdef:
            double look_angle_rad = init_data.look_angle_rad
            double slant_range_ft = init_data.slant_range_ft
            double target_x_ft = init_data.target_x_ft
            double target_y_ft = init_data.target_y_ft
            # double start_height_ft = init_data.start_height_ft  # FIXME: unused definition

        if status == ErrorCode.ZERO_INIT_DONE:  # DONE
            return look_angle_rad

        cdef:
            BaseTrajData_t hit
            BaseTrajSeqT seq
            ErrorCode err
            # early bindings
            double _cZeroFindingAccuracy = self._engine.config.cZeroFindingAccuracy
            int _cMaxIterations = self._engine.config.cMaxIterations

            # Enhanced zero-finding variables
            int iterations_count = 0
            double range_error_ft = 9e9  # Absolute value of error from target distance along sight line
            double prev_range_error_ft = 9e9
            double prev_height_error_ft = 9e9
            double damping_factor = 1.0  # Start with no damping
            double damping_rate = 0.7  # Damping rate for correction
            double last_correction = 0.0
            double height_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line

            # Ensure we can see drop at the target distance when launching along slant angle
            double required_drop_ft = target_x_ft / 2.0 - target_y_ft
            double restore_cMaximumDrop = 0.0
            double restore_cMinimumAltitude = 0.0
            int has_restore_cMaximumDrop = 0
            int has_restore_cMinimumAltitude = 0

            double current_distance, height_diff_ft, look_dist_ft, range_diff_ft
            double trajectory_angle, sensitivity, denominator, correction, applied_correction
            double ca, sa

        # Backup and adjust constraints if needed, then ensure single restore via try/finally
        try:
            if fabs(self._engine.config.cMaximumDrop) < required_drop_ft:
                restore_cMaximumDrop = self._engine.config.cMaximumDrop
                self._engine.config.cMaximumDrop = required_drop_ft
                has_restore_cMaximumDrop = 1

            if (self._engine.config.cMinimumAltitude - shot_props_ptr.alt0) > required_drop_ft:
                restore_cMinimumAltitude = self._engine.config.cMinimumAltitude
                self._engine.config.cMinimumAltitude = shot_props_ptr.alt0 - required_drop_ft
                has_restore_cMinimumAltitude = 1

            while iterations_count < _cMaxIterations:
                # Check height of trajectory at the zero distance (using current barrel_elevation)
                _res = self._integrate(target_x_ft, target_x_ft, 0.0, TrajFlag_t.TFLAG_NONE)
                seq = <BaseTrajSeqT>_res[0]
                err = BaseTrajSeq_t_get_at(&seq._c_view, InterpKey.KEY_POS_X, target_x_ft, -1, &hit)
                if err != ErrorCode.NO_ERROR:
                    raise SolverRuntimeError(
                        f"Failed to interpolate trajectory at target distance, error code: {err}")
                if hit.time == 0.0:
                    # Integrator returned initial point - consider removing constraints
                    break

                current_distance = hit.position.x  # Horizontal distance along X
                if (
                    2 * current_distance < target_x_ft
                    and shot_props_ptr.barrel_elevation == 0.0
                    and look_angle_rad < 1.5
                ):
                    # Degenerate case: little distance and zero elevation; try with some elevation
                    shot_props_ptr.barrel_elevation = 0.01
                    continue

                ca = cos(look_angle_rad)
                sa = sin(look_angle_rad)
                height_diff_ft = hit.position.y * ca - hit.position.x * sa  # slant_height
                look_dist_ft = hit.position.x * ca + hit.position.y * sa  # slant_distance
                range_diff_ft = look_dist_ft - slant_range_ft
                range_error_ft = fabs(range_diff_ft)
                height_error_ft = fabs(height_diff_ft)
                trajectory_angle = atan2(hit.velocity.y, hit.velocity.x)  # Flight angle at current distance

                # Calculate sensitivity and correction
                sensitivity = (
                    tan(shot_props_ptr.barrel_elevation - look_angle_rad)
                    * tan(trajectory_angle - look_angle_rad)
                )
                if sensitivity < -0.5:
                    denominator = look_dist_ft
                else:
                    denominator = look_dist_ft * (1 + sensitivity)

                if fabs(denominator) > 1e-9:
                    correction = -height_diff_ft / denominator
                else:
                    raise ZeroFindingError(
                        height_error_ft,
                        iterations_count,
                        _new_rad(shot_props_ptr.barrel_elevation),
                        'Correction denominator is zero'
                    )

                if range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
                    # We're still trying to reach zero_distance
                    #   We're not getting closer to zero_distance
                    if range_error_ft > prev_range_error_ft - 1e-6:
                        raise ZeroFindingError(
                            range_error_ft,
                            iterations_count,
                            _new_rad(shot_props_ptr.barrel_elevation),
                            'Distance non-convergent'
                        )
                elif height_error_ft > fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                    damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                    if damping_factor < 0.3:
                        raise ZeroFindingError(
                            height_error_ft,
                            iterations_count,
                            _new_rad(shot_props_ptr.barrel_elevation),
                            'Error non-convergent'
                        )
                    # Revert previous adjustment
                    shot_props_ptr.barrel_elevation -= last_correction
                    correction = last_correction
                elif damping_factor < 1.0:
                    damping_factor = 1.0

                prev_range_error_ft = range_error_ft
                prev_height_error_ft = height_error_ft

                if height_error_ft > _cZeroFindingAccuracy or range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
                    # Adjust barrel elevation to close height at zero distance
                    applied_correction = correction * damping_factor
                    shot_props_ptr.barrel_elevation += applied_correction
                    last_correction = applied_correction
                else:  # Current barrel_elevation hit zero: success!
                    break

                iterations_count += 1

        finally:
            # Restore original constraints
            if has_restore_cMaximumDrop:
                self._engine.config.cMaximumDrop = restore_cMaximumDrop
            if has_restore_cMinimumAltitude:
                self._engine.config.cMinimumAltitude = restore_cMinimumAltitude

        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation;
            # so caller can check how close zero is
            raise ZeroFindingError(
                height_error_ft,
                iterations_count,
                _new_rad(shot_props_ptr.barrel_elevation)
            )

        return shot_props_ptr.barrel_elevation

    cdef tuple _integrate(
        CythonizedBaseIntegrationEngine self,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags
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
                str or None: Termination reason if applicable.
        """
        if self._engine.integrate_func_ptr is NULL:
            raise NotImplementedError("integrate_func not implemented or not provided")

        cdef BaseTrajSeqT traj_seq = BaseTrajSeqT()
        cdef ErrorCode err = Engine_t_integrate(
            &self._engine,
            range_limit_ft,
            range_step_ft,
            time_step,
            filter_flags,
            &traj_seq._c_view,
        )
        self._raise_on_input_error(err)

        if err == ErrorCode.NO_ERROR:
            return traj_seq, None

        cdef str termination_reason = None
        if err == ErrorCode.VALUE_ERROR:
            raise ValueError(self.error_message)

        if not isRangeError(err):
            raise SolverRuntimeError(
                f"undefined error in integrate_func, "
                f"error code: {err}, {self.error_message}"
            )

        if err == ErrorCode.RANGE_ERROR_MINIMUM_VELOCITY_REACHED:
            termination_reason = RangeError.MinimumVelocityReached
        elif err == ErrorCode.RANGE_ERROR_MAXIMUM_DROP_REACHED:
            termination_reason = RangeError.MaximumDropReached
        elif err == ErrorCode.RANGE_ERROR_MINIMUM_ALTITUDE_REACHED:
            termination_reason = RangeError.MinimumAltitudeReached

        return traj_seq, termination_reason

    cdef void _raise_on_input_error(CythonizedBaseIntegrationEngine self, ErrorCode err):
        if err == ErrorCode.INPUT_ERROR:
            raise ValueError(f"Invalid input (NULL pointer): {self.error_message}: error code: {err}")

    cdef void _raise_on_apex_error(CythonizedBaseIntegrationEngine self, ErrorCode err):

        if err == ErrorCode.NO_ERROR or isRangeError(err):
            return

        if (err == ErrorCode.VALUE_ERROR):
            raise ValueError("Barrel elevation must be greater than 0 to find apex.")

        if (err == ErrorCode.RUNTIME_ERROR):
            raise SolverRuntimeError("No apex flagged in trajectory data")

        raise RuntimeError(
            f"undefined error occured, "
            f"error code: {err}, {self.error_message}"
        )

    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        ErrorCode err,
        OutOfRangeError_t *err_data
    ):
        if err == ErrorCode.ZERO_INIT_CONTINUE or err == ErrorCode.ZERO_INIT_DONE:
            return

        if err == ErrorCode.OUT_OF_RANGE_ERROR:
            raise OutOfRangeError(
                _new_feet(err_data.requested_distance_ft),
                _new_feet(err_data.max_range_ft),
                _new_rad(err_data.look_angle_rad)
            )

        self._raise_on_apex_error(err)
