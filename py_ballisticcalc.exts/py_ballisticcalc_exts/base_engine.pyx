"""
CythonizedBaseIntegrationEngine

Presently ._integrate() returns dense data in a CBaseTrajSeq, then .integrate()
    feeds it through the Python TrajectoryDataFilter to build List[TrajectoryData].
TODO: Implement a Cython TrajectoryDataFilter for increased speed?
"""
# (Avoid importing cpython.exc; raise Python exceptions directly in cdef functions where needed)
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan2, sqrt, copysign
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t, BaseTrajDataT
import py_ballisticcalc_exts.trajectory_data as td
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT, mag
from py_ballisticcalc_exts.base_traj_seq cimport CBaseTrajSeq, BaseTrajC
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    # types and methods
    Wind_t,
    Atmosphere_t,
    ShotProps_t,
    ShotProps_t_free,
    ShotProps_t_spinDrift,
    ShotProps_t_updateStabilityCoefficient,
    Wind_t_from_python,
    # factory funcs
    Config_t_from_pyobject,
    MachList_t_from_pylist,
    Curve_t_from_pylist,
)

from py_ballisticcalc.conditions import ShotProps
from py_ballisticcalc.engines.base_engine import create_base_engine_config, TrajectoryDataFilter
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine as _PyBaseIntegrationEngine
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag, BaseTrajData, TrajectoryData
from py_ballisticcalc.unit import Angular, Unit, Velocity, Distance, Energy, Weight
cdef double _ALLOWED_ZERO_ERROR_FEET = <double>_PyBaseIntegrationEngine.ALLOWED_ZERO_ERROR_FEET
cdef double _APEX_IS_MAX_RANGE_RADIANS = <double>_PyBaseIntegrationEngine.APEX_IS_MAX_RANGE_RADIANS


__all__ = (
    'CythonizedBaseIntegrationEngine',
)

cdef WindSock_t * WindSock_t_create(object winds_py_list) except NULL:
    """
    Creates and initializes a WindSock_t struct from a Python list of wind objects.
    This function handles the allocation of the struct and its internal Wind_t array.
    """
    cdef WindSock_t * ws = <WindSock_t *>malloc(sizeof(WindSock_t))
    if <void*>ws == NULL:
        raise MemoryError()

    ws.length = <int>len(winds_py_list)
    ws.winds = <Wind_t *>malloc(<size_t>ws.length * sizeof(Wind_t))
    if <void*>ws.winds == NULL:
        free(<void*>ws)
        raise MemoryError()

    cdef int i
    try:
        for i in range(ws.length):
            ws.winds[i] = Wind_t_from_python(winds_py_list[i])
    except Exception:
        free(<void*>ws.winds)
        ws.winds = <Wind_t *>NULL
        free(<void*>ws)
        raise RuntimeError("Invalid wind entry in winds list")

    ws.current = 0
    ws.next_range = cMaxWindDistanceFeet
    ws.last_vector_cache.x = <double>0.0
    ws.last_vector_cache.y = <double>0.0
    ws.last_vector_cache.z = <double>0.0

    # Initialize cache correctly
    WindSock_t_updateCache(ws)

    return ws


cdef class CythonizedBaseIntegrationEngine:
    """Implements EngineProtocol"""
    # Expose Python-visible constants to match BaseIntegrationEngine API
    APEX_IS_MAX_RANGE_RADIANS = float(_APEX_IS_MAX_RANGE_RADIANS)
    ALLOWED_ZERO_ERROR_FEET = float(_ALLOWED_ZERO_ERROR_FEET)

    def __cinit__(CythonizedBaseIntegrationEngine self, object _config):
        self._config = create_base_engine_config(_config)
        self.gravity_vector = V3dT(.0, self._config.cGravityConstant, .0)
        self.integration_step_count = 0

    def __dealloc__(CythonizedBaseIntegrationEngine self):
        self._free_trajectory()

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self):
        return self._config_s.cStepMultiplier

    def find_max_range(self, object shot_info, tuple angle_bracket_deg = (0, 90)):
        """
        Finds the maximum range along shot_info.look_angle, and the launch angle to reach it.
        """
        cdef:
            ShotProps_t* shot_props_ptr
        shot_props_ptr = self._init_trajectory(shot_info)
        try:
            result = self._find_max_range(shot_props_ptr, angle_bracket_deg)
            self._free_trajectory()
            return result
        except:
            self._free_trajectory()
            raise

    def find_zero_angle(self, object shot_info, object distance, bint lofted = False):
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
        using unimodal root-finding that is guaranteed to succeed if a solution exists.
        """
        cdef:
            ShotProps_t* shot_props_ptr
        shot_props_ptr = self._init_trajectory(shot_info)
        try:
            result = self._find_zero_angle(shot_props_ptr, distance._feet, lofted)
            self._free_trajectory()
            return result
        except:
            self._free_trajectory()
            raise

    def find_apex(self, object shot_info) -> TrajectoryData:
        """
        Finds the apex of the trajectory, where apex is defined as the point
        where the vertical component of velocity goes from positive to negative.
        """
        cdef:
            ShotProps_t* shot_props_ptr
        shot_props_ptr = self._init_trajectory(shot_info)
        try:
            result = self._find_apex(shot_props_ptr)
            props = ShotProps.from_shot(shot_info)
            self._free_trajectory()
            return TrajectoryData.from_props(props, result.time, result.position, result.velocity, result.mach)
        except:
            self._free_trajectory()
            raise

    def zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance.
        First tries iterative approach; if that fails falls back on _find_zero_angle.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        cdef:
            ShotProps_t* shot_props_ptr
        shot_props_ptr = self._init_trajectory(shot_info)
        try:
            result = self._zero_angle(shot_props_ptr, distance._feet)
            self._free_trajectory()
            return result
        except ZeroFindingError:
            self._free_trajectory()
            # Fallback to guaranteed method
            shot_props_ptr = self._init_trajectory(shot_info)
            try:
                result = self._find_zero_angle(shot_props_ptr, distance._feet, False)
                self._free_trajectory()
                return result
            except:
                self._free_trajectory()
                raise

    def integrate(CythonizedBaseIntegrationEngine self,
                  object shot_info,
                  object max_range,
                  object dist_step = None,
                  float time_step = 0.0,
                  int filter_flags = 0,
                  bint dense_output = False,
                  **kwargs) -> HitResult:
        """
        Integrates the trajectory for the given shot.

        Args:
            shot_info (Shot): The shot information.
            max_range (Distance): Maximum range of the trajectory (if float then treated as feet).
            dist_step (Optional[Distance]): Distance step for recording RANGE TrajectoryData rows.
            time_step (float, optional): Time step for recording trajectory data. Defaults to 0.0.
            filter_flags (Union[TrajFlag, int], optional): Flags to filter trajectory data. Defaults to TrajFlag.RANGE.
            dense_output (bool, optional): If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult: Object for describing the trajectory.
        """
        cdef:
            ShotProps_t* shot_props_ptr
        range_limit_ft = max_range._feet
        range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft
        shot_props_ptr = self._init_trajectory(shot_info)
        try:
            _res = self._integrate(shot_props_ptr, range_limit_ft, range_step_ft, time_step, filter_flags)
        finally:
            # Always release C resources
            self._free_trajectory()
        props = ShotProps.from_shot(shot_info)
        props.filter_flags = filter_flags
        props.calc_step = self.get_calc_step()  # Add missing calc_step attribute
        
        # Extract trajectory and step_data from the result
        trajectory = _res[0]
        error = _res[1]
        init = trajectory[0]
        tdf = TrajectoryDataFilter(props, filter_flags, init.position_vector, init.velocity_vector,
                                    props.barrel_elevation_rad, props.look_angle_rad,
                                    range_limit_ft, range_step_ft, time_step
        )
        # Feed step_data through TrajectoryDataFilter to get TrajectoryData
        for _, d in enumerate(trajectory):
            tdf.record(BaseTrajData(d.time, d.position_vector, d.velocity_vector, d.mach))
        if error is not None:
            error = RangeError(error, tdf.records)
            # For incomplete trajectories we add last point, so long as it isn't a duplicate
            fin = trajectory[-1]
            if fin.time > tdf.records[-1].time:
                tdf.records.append(TrajectoryData.from_props(props, fin.time, fin.position_vector, fin.velocity_vector, fin.mach, TrajFlag.NONE))
        return HitResult(props, tdf.records, trajectory if dense_output else None, filter_flags != TrajFlag_t.NONE, error)

    cdef inline double _error_at_distance(CythonizedBaseIntegrationEngine self,
                                          ShotProps_t *shot_props_ptr,
                                          double angle_rad,
                                          double target_x_ft,
                                          double target_y_ft):
        """Target miss (feet) for given launch angle using CBaseTrajSeq.
        Attempts to avoid Python exceptions in the hot path by pre-checking reach."""
        cdef:
            CBaseTrajSeq trajectory
            BaseTrajDataT hit
            BaseTrajC* last_ptr
            Py_ssize_t n
        shot_props_ptr[0].barrel_elevation = angle_rad
        __res = self._integrate(shot_props_ptr, target_x_ft, target_x_ft, <double>0.0, <int>TrajFlag_t.NONE)
        trajectory = <CBaseTrajSeq>__res[0]
        # If trajectory is too short for cubic interpolation, treat as unreachable
        n = <Py_ssize_t>len(trajectory)
        if n < <Py_ssize_t>3:
            return <double>9e9
        last_ptr = trajectory.c_getitem(<Py_ssize_t>(-1))
        if last_ptr.time == 0.0:
            # Integrator returned only the initial point; signal unreachable
            return <double>9e9
        try:
            hit = trajectory.get_at('position.x', target_x_ft)
        except Exception:
            # Any interpolation failure (e.g., degenerate points) signals unreachable
            return <double>9e9
        return (hit.position.y - target_y_ft) - fabs(hit.position.x - target_x_ft)

    cdef void _free_trajectory(CythonizedBaseIntegrationEngine self):
        if self._wind_sock != NULL:
            WindSock_t_free(self._wind_sock)
            self._wind_sock = NULL
        ShotProps_t_free(&self._shot_s)

        # After free_trajectory(&self._shot_s), it's good practice to ensure
        # the internal pointers within _shot_s are indeed NULLIFIED for future checks,
        # even if free_trajectory is supposed to do it. This prevents issues if
        # free_trajectory itself doesn't nullify, or if it's called multiple times.
        # (Though your free_curve/free_mach_list don't nullify, so this is important here)
        self._shot_s.mach_list.array = NULL
        self._shot_s.mach_list.length = 0
        self._shot_s.curve.points = NULL
        self._shot_s.curve.length = 0

    cdef ShotProps_t* _init_trajectory(CythonizedBaseIntegrationEngine self, object shot_info):
        """
        Converts Shot properties into floats dimensioned in internal units.

        Args:
            shot_info (Shot): Information about the shot.
        """
        # hack to reload config if it was changed explicit on existed instance
        self._config_s = Config_t_from_pyobject(self._config)
        self.gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)

        self._table_data = shot_info.ammo.dm.drag_table
        # Build C shot struct with robust cleanup on any error that follows
        try:
            self._shot_s = ShotProps_t(
                bc=shot_info.ammo.dm.BC,
                curve=Curve_t_from_pylist(self._table_data),
                mach_list=MachList_t_from_pylist(self._table_data),
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
                diameter=shot_info.ammo.dm.diameter._inch,
                stability_coefficient=0.0,
                filter_flags=0,
                atmo=Atmosphere_t(
                    _t0=shot_info.atmo._t0,
                    _a0=shot_info.atmo._a0,
                    _p0=shot_info.atmo._p0,
                    _mach=shot_info.atmo._mach,
                    density_ratio=shot_info.atmo.density_ratio,
                    cLowestTempC=shot_info.atmo.cLowestTempC,
                )
            )
            self._shot_s.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp)._fps
            if ShotProps_t_updateStabilityCoefficient(&self._shot_s) < 0:
                raise ZeroDivisionError("Zero division detected in ShotProps_t_updateStabilityCoefficient")
        except Exception:
            # Ensure we free any partially allocated arrays inside _shot_s
            ShotProps_t_free(&self._shot_s)
            self._shot_s.mach_list.array = NULL
            self._shot_s.mach_list.length = 0
            self._shot_s.curve.points = NULL
            self._shot_s.curve.length = 0
            raise

        self._wind_sock = WindSock_t_create(shot_info.winds)
        if self._wind_sock is NULL:
            # Free partially constructed shot props before raising
            ShotProps_t_free(&self._shot_s)
            self._shot_s.mach_list.array = NULL
            self._shot_s.mach_list.length = 0
            self._shot_s.curve.points = NULL
            self._shot_s.curve.length = 0
            raise MemoryError("Can't allocate memory for wind_sock")

        return &self._shot_s

    cdef tuple _init_zero_calculation(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance):
        """
        Initializes the zero calculation for the given shot and distance.
        Handles edge cases.
        
        Returns:
            tuple: (status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
            where status is: 0 = CONTINUE, 1 = DONE (early return with look_angle_rad)
        """
        cdef:
            double slant_range_ft = distance
            double look_angle_rad = shot_props_ptr[0].look_angle
            double target_x_ft = slant_range_ft * cos(look_angle_rad)
            double target_y_ft = slant_range_ft * sin(look_angle_rad)
            double start_height_ft = -shot_props_ptr[0].sight_height * shot_props_ptr[0].cant_cosine
            BaseTrajDataT apex
            double apex_slant_ft
        
        # Edge case: Very close shot
        if fabs(slant_range_ft) < _ALLOWED_ZERO_ERROR_FEET:
            return (1, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
        
        # Edge case: Very close shot; ignore gravity and drag
        if fabs(slant_range_ft) < 2.0 * max(fabs(start_height_ft), self._config_s.cStepMultiplier):
            return (1, atan2(target_y_ft + start_height_ft, target_x_ft), slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
        
        # Edge case: Virtually vertical shot; just check if it can reach the target
        if fabs(look_angle_rad - 1.5707963267948966) < _APEX_IS_MAX_RANGE_RADIANS:  # π/2 radians = 90 degrees
            # Compute slant distance at apex using robust accessor
            apex = self._find_apex(shot_props_ptr)
            apex_slant_ft = apex.position.x * cos(look_angle_rad) + apex.position.y * sin(look_angle_rad)
            if apex_slant_ft < slant_range_ft:
                raise OutOfRangeError(_new_feet(distance), _new_feet(apex_slant_ft), _new_rad(look_angle_rad))
            return (1, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
        
        return (0, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)

    cdef object _find_zero_angle(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance, bint lofted):
        """
        Find zero angle using Ridder's method for guaranteed convergence.
        """
        # Get initialization data
        cdef tuple init_data = self._init_zero_calculation(shot_props_ptr, distance)
        cdef:
            int status = <int>init_data[0]
            double look_angle_rad = <double>init_data[1]
            double slant_range_ft = <double>init_data[2]
            double target_x_ft = <double>init_data[3]
            double target_y_ft = <double>init_data[4]
            double start_height_ft = <double>init_data[5]
        
        if status == 1:  # DONE
            return _new_rad(look_angle_rad)
            
        # 1. Find the maximum possible range to establish a search bracket.
        cdef tuple max_range_result = self._find_max_range(shot_props_ptr, (0, 90))
        cdef object max_range = max_range_result[0]
        cdef object angle_at_max = max_range_result[1]
        cdef:
            double max_range_ft = max_range._feet
            double angle_at_max_rad = angle_at_max._rad
            
        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(_new_feet(distance), max_range, _new_rad(look_angle_rad))
        if fabs(slant_range_ft - max_range_ft) < _ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max

        # Backup and adjust constraints (emulate @with_no_minimum_velocity)
        cdef double restore_cMinimumVelocity__zero = <double>0.0
        cdef int has_restore_cMinimumVelocity__zero = 0
        if self._config_s.cMinimumVelocity != <double>0.0:
            restore_cMinimumVelocity__zero = self._config_s.cMinimumVelocity
            self._config_s.cMinimumVelocity = <double>0.0
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

        # Prepare variables for Ridder's method outside of try block to satisfy Cython
        cdef int iteration
        cdef double mid_angle, f_mid, s, next_angle, f_next

        try:
            f_low = self._error_at_distance(shot_props_ptr, low_angle, target_x_ft, target_y_ft)
            # If low is exactly look angle and failed to evaluate, nudge slightly upward to bracket
            if f_low > <double>1e8 and fabs(low_angle - look_angle_rad) < <double>1e-9:
                low_angle = look_angle_rad + <double>1e-3
                f_low = self._error_at_distance(shot_props_ptr, low_angle, target_x_ft, target_y_ft)
            f_high = self._error_at_distance(shot_props_ptr, high_angle, target_x_ft, target_y_ft)

            if f_low * f_high >= 0:
                lofted_str = "lofted" if lofted else "low"
                reason = f"No {lofted_str} zero trajectory in elevation range "
                reason += f"({low_angle * 57.29577951308232:.2f}, "  # Convert to degrees
                reason += f"{high_angle * 57.29577951308232:.2f} deg). "
                reason += f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
                raise ZeroFindingError(float(target_y_ft), 0, _new_rad(<double>shot_props_ptr[0].barrel_elevation), reason=reason)

            # 4. Ridder's method implementation
            for iteration in range(<int>self._config_s.cMaxIterations):
                mid_angle = (low_angle + high_angle) / 2.0
                f_mid = self._error_at_distance(shot_props_ptr, mid_angle, target_x_ft, target_y_ft)

                # s is the updated point using the root of the linear function through (low_angle, f_low) and (high_angle, f_high)
                # and the quadratic function that passes through those points and (mid_angle, f_mid)
                s = sqrt(f_mid * f_mid - f_low * f_high)
                if s == 0.0:
                    break  # Should not happen if f_low and f_high have opposite signs

                next_angle = mid_angle + (mid_angle - low_angle) * (copysign(<double>1.0, f_low - f_high) * f_mid / s)
                if fabs(next_angle - mid_angle) < self._config_s.cZeroFindingAccuracy:
                    return _new_rad(next_angle)

                f_next = self._error_at_distance(shot_props_ptr, next_angle, target_x_ft, target_y_ft)
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

                if fabs(high_angle - low_angle) < self._config_s.cZeroFindingAccuracy:
                    return _new_rad((low_angle + high_angle) / 2)

            raise ZeroFindingError(float(target_y_ft), <int>self._config_s.cMaxIterations, _new_rad((low_angle + high_angle) / 2),
                                   reason="Ridder's method failed to converge.")
        finally:
            if has_restore_cMinimumVelocity__zero:
                self._config_s.cMinimumVelocity = restore_cMinimumVelocity__zero

    cdef tuple _find_max_range(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, tuple angle_bracket_deg = (0, 90)):
        """
        Internal function to find the maximum slant range via golden-section search.

        Args:
            props (ShotProps): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for max range.
                                                               Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum slant range and the launch angle to reach it.
        """
        cdef:
            double look_angle_rad = <double>shot_props_ptr[0].look_angle
            double low_angle_deg = <double>angle_bracket_deg[0]
            double high_angle_deg = <double>angle_bracket_deg[1]
            double max_range_ft
            double angle_at_max_rad
            BaseTrajDataT _apex_obj
            double _sdist
            
        # Virtually vertical shot
        if fabs(look_angle_rad - <double>1.5707963267948966) < _APEX_IS_MAX_RANGE_RADIANS:  # π/2 radians = 90 degrees
            _apex_obj = self._find_apex(shot_props_ptr)
            _sdist = _apex_obj.position.x * cos(look_angle_rad) + _apex_obj.position.y * sin(look_angle_rad)
            return (_new_feet(_sdist), _new_rad(look_angle_rad))
        
        # Backup and adjust constraints (emulate @with_max_drop_zero and @with_no_minimum_velocity)
        cdef:
            double restore_cMaximumDrop = <double>0.0
            int has_restore_cMaximumDrop = 0
            double restore_cMinimumVelocity = <double>0.0
            int has_restore_cMinimumVelocity = 0
            
        if self._config_s.cMaximumDrop != <double>0.0:
            restore_cMaximumDrop = self._config_s.cMaximumDrop
            self._config_s.cMaximumDrop = <double>0.0  # We want to run trajectory until it returns to horizontal
            has_restore_cMaximumDrop = 1
        if self._config_s.cMinimumVelocity != <double>0.0:
            restore_cMinimumVelocity = self._config_s.cMinimumVelocity
            self._config_s.cMinimumVelocity = <double>0.0
            has_restore_cMinimumVelocity = 1
        
        cdef:
            double inv_phi = <double>0.6180339887498949  # (sqrt(5) - 1) / 2
            double inv_phi_sq = <double>0.38196601125010515  # inv_phi^2
            double a = low_angle_deg * <double>0.017453292519943295  # Convert to radians
            double b = high_angle_deg * <double>0.017453292519943295  # Convert to radians
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
            cdef CBaseTrajSeq trajectory
            cdef Py_ssize_t n
            cdef Py_ssize_t i
            cdef BaseTrajC* prev_ptr
            cdef BaseTrajC* cur_ptr
            # Update shot data
            shot_props_ptr[0].barrel_elevation = angle_rad
            try:
                _res = self._integrate(shot_props_ptr, <double>(9e9), <double>(9e9), <double>(0.0), <int>TrajFlag_t.NONE)
                trajectory = <CBaseTrajSeq>_res[0]
                ca = cos(shot_props_ptr[0].look_angle)
                sa = sin(shot_props_ptr[0].look_angle)
                n = <Py_ssize_t>len(trajectory)
                if n >= 2:
                    # Linear search from end of trajectory for zero-down crossing
                    for i in range(n - 1, 0, -1):
                        prev_ptr = trajectory.c_getitem(i - 1)
                        cur_ptr = trajectory.c_getitem(i)
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
        
        yc = <double>float(range_for_angle(c))
        yd = <double>float(range_for_angle(d))
        
        # Golden-section search
        for iteration in range(100):  # 100 iterations is more than enough for high precision
            if h < <double>1e-5:  # Angle tolerance in radians
                break
            if yc > yd:
                b, d, yd = d, c, yc
                h = b - a
                c = a + inv_phi_sq * h
                yc = <double>float(range_for_angle(c))
            else:
                a, c, yc = c, d, yd
                h = b - a
                d = a + inv_phi * h
                yd = <double>float(range_for_angle(d))
        
        angle_at_max_rad = (a + b) / 2
        max_range_ft = <double>float(range_for_angle(angle_at_max_rad))
        
    # Restore original constraints
        if has_restore_cMaximumDrop:
            self._config_s.cMaximumDrop = restore_cMaximumDrop
        if has_restore_cMinimumVelocity:
            self._config_s.cMinimumVelocity = restore_cMinimumVelocity
        
        return (_new_feet(max_range_ft), _new_rad(angle_at_max_rad))

    cdef BaseTrajDataT _find_apex(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr):
        """
        Internal implementation to find the apex of the trajectory.
        """
        if shot_props_ptr[0].barrel_elevation <= 0:
            raise ValueError("Barrel elevation must be greater than 0 to find apex.")
        
        # Have to ensure cMinimumVelocity is 0 for this to work
        cdef:
            double restore_min_velocity = <double>0.0
            int has_restore_min_velocity = 0
            BaseTrajDataT apex
            tuple _res

        if self._config_s.cMinimumVelocity > <double>0.0:
            restore_min_velocity = self._config_s.cMinimumVelocity
            self._config_s.cMinimumVelocity = <double>0.0
            has_restore_min_velocity = 1
        
        try:
            _res = self._integrate(shot_props_ptr, <double>9e9, <double>9e9, <double>0.0, <int>TrajFlag_t.APEX)
            apex = (<CBaseTrajSeq>_res[0]).get_at('velocity.y', 0.0)
        finally:
            if has_restore_min_velocity:
                self._config_s.cMinimumVelocity = restore_min_velocity
        
        if not apex:
            raise SolverRuntimeError("No apex flagged in trajectory data")
        
        return apex

    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance):
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
        cdef tuple init_data = self._init_zero_calculation(shot_props_ptr, distance)
        cdef:
            int status = <int>init_data[0]
            double look_angle_rad = <double>init_data[1]
            double slant_range_ft = <double>init_data[2]
            double target_x_ft = <double>init_data[3]
            double target_y_ft = <double>init_data[4]
            double start_height_ft = <double>init_data[5]
        
        if status == 1:  # DONE
            return _new_rad(look_angle_rad)

        cdef:
            BaseTrajDataT hit
            # early bindings
            double _cZeroFindingAccuracy = self._config_s.cZeroFindingAccuracy
            int _cMaxIterations = <int>self._config_s.cMaxIterations

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
            if fabs(self._config_s.cMaximumDrop) < required_drop_ft:
                restore_cMaximumDrop = self._config_s.cMaximumDrop
                self._config_s.cMaximumDrop = required_drop_ft
                has_restore_cMaximumDrop = 1
            
            if (self._config_s.cMinimumAltitude - shot_props_ptr[0].alt0) > required_drop_ft:
                restore_cMinimumAltitude = self._config_s.cMinimumAltitude
                self._config_s.cMinimumAltitude = shot_props_ptr[0].alt0 - required_drop_ft
                has_restore_cMinimumAltitude = 1

            while iterations_count < _cMaxIterations:
                # Check height of trajectory at the zero distance (using current barrel_elevation)
                _res = self._integrate(shot_props_ptr, target_x_ft, target_x_ft, <double>0.0, <int>TrajFlag_t.NONE)
                hit = (<CBaseTrajSeq>_res[0]).get_at('position.x', <double>target_x_ft)

                if hit.time == 0.0:
                    # Integrator returned initial point - consider removing constraints
                    break

                current_distance = hit.position.x  # Horizontal distance along X
                if 2 * current_distance < target_x_ft and shot_props_ptr[0].barrel_elevation == 0.0 and look_angle_rad < 1.5:
                    # Degenerate case: little distance and zero elevation; try with some elevation
                    shot_props_ptr[0].barrel_elevation = 0.01
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
                sensitivity = tan(shot_props_ptr[0].barrel_elevation - look_angle_rad) * tan(trajectory_angle - look_angle_rad)
                if sensitivity < -0.5:
                    denominator = look_dist_ft
                else:
                    denominator = look_dist_ft * (1 + sensitivity)
                
                if fabs(denominator) > 1e-9:
                    correction = -height_diff_ft / denominator
                else:
                    raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>shot_props_ptr[0].barrel_elevation),
                                         'Correction denominator is zero')

                if range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
                    # We're still trying to reach zero_distance
                    if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                        raise ZeroFindingError(range_error_ft, iterations_count, _new_rad(<double>shot_props_ptr[0].barrel_elevation),
                                             'Distance non-convergent')
                elif height_error_ft > fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                    damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                    if damping_factor < 0.3:
                        raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>shot_props_ptr[0].barrel_elevation),
                                             'Error non-convergent')
                    # Revert previous adjustment
                    shot_props_ptr[0].barrel_elevation -= last_correction
                    correction = last_correction
                elif damping_factor < 1.0:
                    damping_factor = 1.0

                prev_range_error_ft = range_error_ft
                prev_height_error_ft = height_error_ft

                if height_error_ft > _cZeroFindingAccuracy or range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
                    # Adjust barrel elevation to close height at zero distance
                    applied_correction = correction * damping_factor
                    shot_props_ptr[0].barrel_elevation += applied_correction
                    last_correction = applied_correction
                else:  # Current barrel_elevation hit zero: success!
                    break
                
                iterations_count += 1

        finally:
            # Restore original constraints
            if has_restore_cMaximumDrop:
                self._config_s.cMaximumDrop = restore_cMaximumDrop
            if has_restore_cMinimumAltitude:
                self._config_s.cMinimumAltitude = restore_cMinimumAltitude

        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > _ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>shot_props_ptr[0].barrel_elevation))
        
        return _new_rad(<double>shot_props_ptr[0].barrel_elevation)


    cdef tuple _integrate(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr,
                          double range_limit_ft, double range_step_ft,
                          double time_step, int filter_flags):
        raise NotImplementedError


cdef object create_trajectory_row(double time, const V3dT *range_vector_ptr, const V3dT *velocity_vector_ptr,
                                  double mach, const ShotProps_t *shot_props_ptr,
                                  double density_ratio, double drag, int flag):

    cdef:
        double look_angle = shot_props_ptr.look_angle
        double spin_drift = ShotProps_t_spinDrift(shot_props_ptr, time)
        double velocity = mag(velocity_vector_ptr)
        double windage = range_vector_ptr.z + spin_drift
        double drop_angleustment = getCorrection(range_vector_ptr.x, range_vector_ptr.y)
        double windage_angleustment = getCorrection(range_vector_ptr.x, windage)
        double trajectory_angle = atan2(velocity_vector_ptr.y, velocity_vector_ptr.x);
        double look_angle_cos = cos(look_angle)
        double look_angle_sin = sin(look_angle)

    drop_angleustment -= (look_angle if range_vector_ptr.x else 0)

    # Note: Cython cdef class constructors don't support keyword args reliably from Cython.
    # Pass all fields positionally in the defined order.
    return td.TrajectoryData(
        time,
        _new_feet(range_vector_ptr.x),
        _new_fps(velocity),
        velocity / mach,
        _new_feet(range_vector_ptr.y),
        _new_feet(range_vector_ptr.y * look_angle_cos - range_vector_ptr.x * look_angle_sin),
        _new_rad(drop_angleustment),
        _new_feet(windage),
        _new_rad(windage_angleustment),
        _new_feet(range_vector_ptr.x * look_angle_cos + range_vector_ptr.y * look_angle_sin),
        _new_rad(trajectory_angle),
        density_ratio,
        drag,
        _new_ft_lb(calculateEnergy(shot_props_ptr.weight, velocity)),
        _new_lb(calculateOgw(shot_props_ptr.weight, velocity)),
        flag
    )


cdef object _new_feet(double v):
    return Distance(float(v), Unit.Foot)


cdef object _new_fps(double v):
    return Velocity(float(v), Unit.FPS)


cdef object _new_rad(double v):
    return Angular(float(v), Unit.Radian)


cdef object _new_ft_lb(double v):
    return Energy(float(v), Unit.FootPound)


cdef object _new_lb(double v):
    return Weight(float(v), Unit.Pound)
