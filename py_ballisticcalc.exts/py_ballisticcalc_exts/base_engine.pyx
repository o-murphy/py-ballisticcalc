# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cython.cimports.cpython cimport exc
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, sqrt, copysign
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    # types and methods
    Config_t,
    Wind_t,
    Atmosphere_t,
    ShotData_t,
    ShotData_t_free,
    ShotData_t_spinDrift,
    ShotData_t_updateStabilityCoefficient,
    Wind_t_from_python,
    Wind_t_to_V3dT,
    # factory funcs
    Config_t_from_pyobject,
    MachList_t_from_pylist,
    Curve_t_from_pylist,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT, add, sub, mag, mulS
)

from py_ballisticcalc.unit import Angular, Unit, Velocity, Distance, Energy, Weight
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.engines.base_engine import create_base_engine_config
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag


__all__ = (
    'CythonizedBaseIntegrationEngine',
    'create_trajectory_row',
)


cdef TrajDataFilter_t TrajDataFilter_t_create(int filter_flags, double range_step,
                  const V3dT *initial_position_ptr, const V3dT *initial_velocity_ptr,
                  double time_step = 0.0):
    return TrajDataFilter_t(
        filter_flags, TrajFlag_t.NONE, TrajFlag_t.NONE,
        time_step, range_step,
        0.0, 0.0, 0.0, 0.0,
        initial_position_ptr[0],
        initial_velocity_ptr[0],
        0.0, 0.0,
    )

cdef void TrajDataFilter_t_setup_seen_zero(TrajDataFilter_t * tdf, double height, const ShotData_t *shot_data_ptr):
    if height >= 0:
        tdf.seen_zero |= TrajFlag_t.ZERO_UP
    elif height < 0 and shot_data_ptr.barrel_elevation < shot_data_ptr.look_angle:
        tdf.seen_zero |= TrajFlag_t.ZERO_DOWN
    tdf.look_angle = shot_data_ptr.look_angle

cdef BaseTrajData TrajDataFilter_t_should_record(TrajDataFilter_t * tdf, const V3dT *position_ptr, const V3dT *velocity_ptr, double mach, double time):
    cdef BaseTrajData data = None
    cdef double ratio
    cdef V3dT temp_position, temp_velocity
    cdef V3dT temp_sub_position, temp_sub_velocity
    cdef V3dT temp_mul_position, temp_mul_velocity

    tdf.current_flag = TrajFlag_t.NONE
    if (tdf.range_step > 0) and (position_ptr.x >= tdf.next_record_distance):
        while tdf.next_record_distance + tdf.range_step < position_ptr.x:
            # Handle case where we have stepped past more than one record distance
            tdf.next_record_distance += tdf.range_step
        if position_ptr.x > tdf.previous_position.x:
            # Interpolate to get BaseTrajData at the record distance
            ratio = (tdf.next_record_distance - tdf.previous_position.x) / (position_ptr.x - tdf.previous_position.x)
            temp_sub_position = sub(position_ptr, &tdf.previous_position)
            temp_mul_position = mulS(&temp_sub_position, ratio)
            temp_position = add(&tdf.previous_position, &temp_mul_position)
            temp_sub_velocity = sub(velocity_ptr, &tdf.previous_velocity)
            temp_mul_velocity = mulS(&temp_sub_velocity, ratio)
            temp_velocity = add(&tdf.previous_velocity, &temp_mul_velocity)
            data = BaseTrajData(
                time=tdf.previous_time + (time - tdf.previous_time) * ratio,
                position=temp_position,
                velocity=temp_velocity,
                mach=tdf.previous_mach + (mach - tdf.previous_mach) * ratio
            )
        tdf.current_flag |= TrajFlag_t.RANGE
        tdf.next_record_distance += tdf.range_step
        tdf.time_of_last_record = time
    elif tdf.time_step > 0:
        _check_next_time(tdf, time)
    if tdf.filter & TrajFlag_t.ZERO:
        _check_zero_crossing(tdf, position_ptr)
    if tdf.filter & TrajFlag_t.MACH:
        _check_mach_crossing(tdf, mag(velocity_ptr), mach)
    if tdf.filter & TrajFlag_t.APEX:
        _check_apex(tdf, velocity_ptr)
    if (tdf.current_flag & tdf.filter) != 0 and data is None:
        data = BaseTrajData(time=time, position=position_ptr[0],
                            velocity=velocity_ptr[0], mach=mach)
    tdf.previous_time = time
    tdf.previous_position = position_ptr[0]
    tdf.previous_velocity = velocity_ptr[0]
    tdf.previous_mach = mach
    return data

cdef void _check_next_time(TrajDataFilter_t * tdf, double time):
    if time > tdf.time_of_last_record + tdf.time_step:
        tdf.current_flag |= TrajFlag_t.RANGE
        tdf.time_of_last_record = time

cdef void _check_mach_crossing(TrajDataFilter_t * tdf, double velocity, double mach):
    cdef double current_v_mach = velocity / mach
    if tdf.previous_v_mach > 1 >= current_v_mach:
        tdf.current_flag |= TrajFlag_t.MACH
    tdf.previous_v_mach = current_v_mach

cdef void _check_zero_crossing(TrajDataFilter_t * tdf, const V3dT *range_vector_ptr):
    if range_vector_ptr.x > 0:
        # Zero reference line is the sight line defined by look_angle
        reference_height = range_vector_ptr.x * tan(tdf.look_angle)
        # If we haven't seen ZERO_UP, we look for that first
        if not (tdf.seen_zero & TrajFlag_t.ZERO_UP):
            if range_vector_ptr.y >= reference_height:
                tdf.current_flag |= TrajFlag_t.ZERO_UP
                tdf.seen_zero |= TrajFlag_t.ZERO_UP
        # We've crossed above sight line; now look for crossing back through it
        elif not (tdf.seen_zero & TrajFlag_t.ZERO_DOWN):
            if range_vector_ptr.y < reference_height:
                tdf.current_flag |= TrajFlag_t.ZERO_DOWN
                tdf.seen_zero |= TrajFlag_t.ZERO_DOWN

cdef void _check_apex(TrajDataFilter_t * tdf, const V3dT *velocity_vector_ptr):
    if velocity_vector_ptr.y <= 0 and tdf.previous_velocity.y > 0:
        # We have crossed the apex
        tdf.current_flag |= TrajFlag_t.APEX


cdef WindSock_t * WindSock_t_create(object winds_py_list):
    """
    Creates and initializes a WindSock_t struct from a Python list of wind objects.
    This function handles the allocation of the struct and its internal Wind_t array.
    """
    cdef WindSock_t * ws = <WindSock_t *>malloc(sizeof(WindSock_t))
    if ws is NULL:
        # Handle memory allocation failure (e.g., raise a MemoryError)
        # Since this is pure Cython, you might opt for error codes or propagate exceptions.
        # For now, let's print and return NULL.
        exc.PyErr_NoMemory() # Set Python's MemoryError
        return NULL

    ws.length = len(winds_py_list)
    ws.winds = <Wind_t *>malloc(ws.length * sizeof(Wind_t))

    if ws.winds is NULL:
        # Handle memory allocation failure for winds array
        free(ws) # Free the outer struct as well
        exc.PyErr_NoMemory()
        return NULL

    cdef int i
    for i in range(ws.length):
        ws.winds[i] = Wind_t_from_python(winds_py_list[i])

    ws.current = 0
    ws.next_range = cMaxWindDistanceFeet
    ws.last_vector_cache.x = 0.0
    ws.last_vector_cache.y = 0.0
    ws.last_vector_cache.z = 0.0

    # Initialize cache correctly
    WindSock_t_updateCache(ws)

    return ws


cdef class CythonizedBaseIntegrationEngine:

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
        self._init_trajectory(shot_info)
        try:
            result = self._find_max_range(shot_info, angle_bracket_deg)
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
        self._init_trajectory(shot_info)
        try:
            result = self._find_zero_angle(shot_info, distance, lofted)
            self._free_trajectory()
            return result
        except:
            self._free_trajectory()
            raise

    def find_apex(self, object shot_info):
        """
        Finds the apex of the trajectory, where apex is defined as the point
        where the vertical component of velocity goes from positive to negative.
        """
        self._init_trajectory(shot_info)
        try:
            result = self._find_apex(shot_info)
            self._free_trajectory()
            return result
        except:
            self._free_trajectory()
            raise

    def zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance) -> Angular:
        self._init_trajectory(shot_info)
        try:
            result = self._zero_angle(shot_info, distance)
            self._free_trajectory()
            return result
        except ZeroFindingError as e:
            self._free_trajectory()
            # Fallback to guaranteed method
            self._init_trajectory(shot_info)
            try:
                result = self._find_zero_angle(shot_info, distance, False)
                self._free_trajectory()
                return result
            except:
                self._free_trajectory()
                raise

    def integrate(CythonizedBaseIntegrationEngine self,
                  object shot_info,
                  object max_range,
                  object dist_step = None,
                  double time_step = 0.0,
                  TrajFlag_t filter_flags = TrajFlag_t.NONE,
                  bint dense_output = False,
                  **kwargs) -> object:
        range_limit_ft = max_range._feet
        range_step_ft = dist_step._feet if dist_step is not None else range_limit_ft

        self._init_trajectory(shot_info)
        object = self._integrate(range_limit_ft, range_step_ft, time_step, filter_flags, dense_output)
        self._free_trajectory()
        return HitResult(shot_info, object[0], filter_flags > 0, object[1])

    cdef void _free_trajectory(CythonizedBaseIntegrationEngine self):
        if self._wind_sock is not NULL:
            WindSock_t_free(self._wind_sock)
            self._wind_sock = NULL
        ShotData_t_free(&self._shot_s)

        # After free_trajectory(&self._shot_s), it's good practice to ensure
        # the internal pointers within _shot_s are indeed NULLIFIED for future checks,
        # even if free_trajectory is supposed to do it. This prevents issues if
        # free_trajectory itself doesn't nullify, or if it's called multiple times.
        # (Though your free_curve/free_mach_list don't nullify, so this is important here)
        self._shot_s.mach_list.array = NULL
        self._shot_s.mach_list.length = 0
        self._shot_s.curve.points = NULL
        self._shot_s.curve.length = 0

    cdef void _init_trajectory(CythonizedBaseIntegrationEngine self, object shot_info):
        # hack to reload config if it was changed explicit on existed instance
        self._config_s = Config_t_from_pyobject(self._config)
        self.gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)

        self._table_data = shot_info.ammo.dm.drag_table
        self._shot_s = ShotData_t(
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
        if ShotData_t_updateStabilityCoefficient(&self._shot_s) < 0:
            raise ZeroDivisionError("Zero division detected in ShotData_t_updateStabilityCoefficient")

        self._wind_sock = WindSock_t_create(shot_info.winds)
        if self._wind_sock is NULL:
            raise MemoryError("Can't allocate memory for wind_sock")

    cdef tuple _init_zero_calculation(CythonizedBaseIntegrationEngine self, object shot_info, object distance):
        """
        Initializes the zero calculation for the given shot and distance.
        Handles edge cases.
        
        Returns:
            tuple: (status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
            where status is: 0 = CONTINUE, 1 = DONE (early return with look_angle_rad)
        """
        cdef:
            double ALLOWED_ZERO_ERROR_FEET = 0.01
            double APEX_IS_MAX_RANGE_RADIANS = 0.0003
            double slant_range_ft = distance._feet
            double look_angle_rad = shot_info.look_angle._rad
            double target_x_ft = slant_range_ft * cos(look_angle_rad)
            double target_y_ft = slant_range_ft * sin(look_angle_rad)
            double start_height_ft = -shot_info.weapon.sight_height._feet * cos(shot_info.cant_angle._rad)
        
        # Edge case: Very close shot
        if fabs(slant_range_ft) < ALLOWED_ZERO_ERROR_FEET:
            return (1, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
        
        # Edge case: Very close shot; ignore gravity and drag
        if fabs(slant_range_ft) < 2.0 * max(fabs(start_height_ft), self._config_s.cStepMultiplier):
            return (1, atan2(target_y_ft + start_height_ft, target_x_ft), slant_range_ft, target_x_ft, target_y_ft, start_height_ft)
        
        # Edge case: Virtually vertical shot; just check if it can reach the target
        if fabs(look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS:  # π/2 radians = 90 degrees
            # For now, continue with normal algorithm
            # TODO: implement _find_apex check for reachability
            pass
        
        return (0, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)

    cdef object _find_zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance, bint lofted):
        """
        Find zero angle using Ridder's method for guaranteed convergence.
        """
        # Get initialization data
        cdef tuple init_data = self._init_zero_calculation(shot_info, distance)
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
        cdef tuple max_range_result = self._find_max_range(shot_info, (0, 90))
        cdef object max_range = max_range_result[0]
        cdef object angle_at_max = max_range_result[1]
        cdef:
            double max_range_ft = max_range._feet
            double angle_at_max_rad = angle_at_max._rad
            double ALLOWED_ZERO_ERROR_FEET = <double>0.01
            
        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(distance, max_range, _new_rad(look_angle_rad))
        if fabs(slant_range_ft - max_range_ft) < ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max
        
        def error_at_distance(angle_rad):
            """Target miss (in feet) for given launch angle."""
            self._shot_s.barrel_elevation = angle_rad
            try:
                t = self._integrate(<double>(9e9), <double>(9e9), <double>(0.0), <int>TrajFlag_t.NONE, <bint>False)[0][-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            if t.time == <double>0.0:
                # logger.warning("Integrator returned initial point. Consider removing constraints.")
                return <double>9e9
            return (t.height._feet) - target_y_ft - fabs((t.distance._feet) - target_x_ft)
        
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
        
        f_low = error_at_distance(low_angle)
        f_high = error_at_distance(high_angle)
        
        if f_low * f_high >= 0:
            lofted_str = "lofted" if lofted else "low"
            reason = f"No {lofted_str} zero trajectory in elevation range "
            reason += f"({low_angle * 57.29577951308232:.2f}, "  # Convert to degrees
            reason += f"{high_angle * 57.29577951308232:.2f} deg). "
            reason += f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
            raise ZeroFindingError(target_y_ft, 0, _new_rad(self._shot_s.barrel_elevation), reason=reason)
        
        # 4. Ridder's method implementation
        cdef:
            int iteration
            double mid_angle, f_mid, s, next_angle, f_next
            
        for iteration in range(<int>self._config_s.cMaxIterations):
            mid_angle = (low_angle + high_angle) / 2.0
            f_mid = error_at_distance(mid_angle)
            
            # s is the updated point using the root of the linear function through (low_angle, f_low) and (high_angle, f_high)
            # and the quadratic function that passes through those points and (mid_angle, f_mid)
            s = sqrt(f_mid * f_mid - f_low * f_high)
            if s == 0.0:
                break  # Should not happen if f_low and f_high have opposite signs
            
            next_angle = mid_angle + (mid_angle - low_angle) * (copysign(1.0, f_low - f_high) * f_mid / s)
            if fabs(next_angle - mid_angle) < self._config_s.cZeroFindingAccuracy:
                return _new_rad(next_angle)
            
            f_next = error_at_distance(next_angle)
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
        
        raise ZeroFindingError(target_y_ft, <int>self._config_s.cMaxIterations, _new_rad((low_angle + high_angle) / 2),
                               reason="Ridder's method failed to converge.")

    cdef tuple _find_max_range(CythonizedBaseIntegrationEngine self, object shot_info, tuple angle_bracket_deg = (0, 90)):
        """
        Internal function to find the maximum slant range via golden-section search.
        """
        cdef:
            double APEX_IS_MAX_RANGE_RADIANS = <double>0.0003
            double look_angle_rad = shot_info.look_angle._rad
            double low_angle_deg = <double>angle_bracket_deg[0]
            double high_angle_deg = <double>angle_bracket_deg[1]
            double max_range_ft
            double angle_at_max_rad
            object max_range_distance, angle_result
            
        # Virtually vertical shot
        if fabs(look_angle_rad - <double>1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS:  # π/2 radians = 90 degrees
            apex_result = self._find_apex(shot_info)
            max_range_distance = apex_result.slant_distance
            angle_result = _new_rad(look_angle_rad)
            return (max_range_distance, angle_result)
        
        # if look_angle_rad > 0:
        #     warnings.warn("Code does not yet support non-horizontal look angles.", UserWarning)
        
        # Backup and adjust constraints
        cdef:
            double restore_cMaximumDrop = <double>0.0
            int has_restore_cMaximumDrop = 0
            
        if self._config_s.cMaximumDrop != <double>0.0:
            restore_cMaximumDrop = self._config_s.cMaximumDrop
            self._config_s.cMaximumDrop = <double>0.0  # We want to run trajectory until it returns to horizontal
            has_restore_cMaximumDrop = 1
        
        cdef:
            int t_calls = 0
            dict cache = {}
            double inv_phi = <double>0.6180339887498949  # (sqrt(5) - 1) / 2
            double inv_phi_sq = <double>0.38196601125010515  # inv_phi^2
            double a = low_angle_deg * <double>0.017453292519943295  # Convert to radians
            double b = high_angle_deg * <double>0.017453292519943295  # Convert to radians
            double h = b - a
            double c = a + inv_phi_sq * h
            double d = a + inv_phi * h
            double yc, yd
            int iteration
            object t
            
        def range_for_angle(angle_rad):
            """Horizontal range to zero (in feet) for given launch angle in radians."""
            if angle_rad in cache:
                return cache[angle_rad]
            
            # Update shot data
            self._shot_s.barrel_elevation = angle_rad
            
            try:
                t = self._integrate(<double>(9e9), <double>(9e9), <double>(0.0), <int>TrajFlag_t.NONE, <bint>False)[0][-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            
            range_ft = t.distance._feet
            cache[angle_rad] = range_ft
            return range_ft
        
        yc = range_for_angle(c)
        yd = range_for_angle(d)
        
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
            self._config_s.cMaximumDrop = restore_cMaximumDrop
        
        return (_new_feet(max_range_ft), _new_rad(angle_at_max_rad))

    cdef object _find_apex(CythonizedBaseIntegrationEngine self, object shot_info):
        """
        Internal implementation to find the apex of the trajectory.
        """
        if self._shot_s.barrel_elevation <= 0:
            raise ValueError("Barrel elevation must be greater than 0 to find apex.")
        
        # Have to ensure cMinimumVelocity is 0 for this to work
        cdef:
            double restore_min_velocity = <double>0.0
            int has_restore_min_velocity = 0
            object hit_result, apex
        
        if self._config_s.cMinimumVelocity > <double>0.0:
            restore_min_velocity = self._config_s.cMinimumVelocity
            self._config_s.cMinimumVelocity = <double>0.0
            has_restore_min_velocity = 1
        
        try:
            trajectory = self._integrate(<double>9e9, <double>9e9, <double>0.0, <int>TrajFlag.APEX, <bint>False)[0]
            hit_result = HitResult(shot_info, trajectory, extra=True)
        except RangeError as e:
            if e.last_distance is None:
                raise e
            hit_result = HitResult(shot_info, e.incomplete_trajectory, extra=True)

        if has_restore_min_velocity:
            self._config_s.cMinimumVelocity = restore_min_velocity
        
        apex = hit_result.flag(TrajFlag.APEX)
        if not apex:
            raise SolverRuntimeError("No apex flagged in trajectory data")
        
        return apex

    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance):
        """
        Iterative algorithm to find barrel elevation needed for a particular zero.
        Enhanced version with better convergence and error handling.
        """
        # Get initialization data using the new method
        cdef tuple init_data = self._init_zero_calculation(shot_info, distance)
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
            # early bindings
            double _cZeroFindingAccuracy = self._config_s.cZeroFindingAccuracy
            int _cMaxIterations = <int>self._config_s.cMaxIterations
            double ALLOWED_ZERO_ERROR_FEET = 0.01  # Allowed range error (along sight line), in feet, for zero angle

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

            object t
            double current_distance, height_diff_ft, look_dist_ft, range_diff_ft
            double trajectory_angle, sensitivity, denominator, correction, applied_correction

        # Backup and adjust constraints if needed
        if fabs(self._config_s.cMaximumDrop) < required_drop_ft:
            restore_cMaximumDrop = self._config_s.cMaximumDrop
            self._config_s.cMaximumDrop = required_drop_ft
            has_restore_cMaximumDrop = 1
        
        if (self._config_s.cMinimumAltitude - shot_info.atmo.altitude._feet) > required_drop_ft:
            restore_cMinimumAltitude = self._config_s.cMinimumAltitude
            self._config_s.cMinimumAltitude = shot_info.atmo.altitude._feet - required_drop_ft
            has_restore_cMinimumAltitude = 1

        while iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current barrel_elevation)
            try:
                t = self._integrate(target_x_ft, target_x_ft, <double>0.0, <int>TrajFlag_t.NONE, <bint>False)[0][-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            
            if t.time == 0.0:
                # Integrator returned initial point - consider removing constraints
                break

            current_distance = t.distance._feet  # Horizontal distance
            if 2 * current_distance < target_x_ft and self._shot_s.barrel_elevation == 0.0 and look_angle_rad < 1.5:
                # Degenerate case: little distance and zero elevation; try with some elevation
                self._shot_s.barrel_elevation = 0.01
                continue

            height_diff_ft = t.slant_height._feet
            look_dist_ft = t.slant_distance._feet
            range_diff_ft = look_dist_ft - slant_range_ft
            range_error_ft = fabs(range_diff_ft)
            height_error_ft = fabs(height_diff_ft)
            trajectory_angle = t.angle._rad  # Flight angle at current distance
            
            # Calculate sensitivity and correction
            sensitivity = tan(self._shot_s.barrel_elevation - look_angle_rad) * tan(trajectory_angle - look_angle_rad)
            if sensitivity < -0.5:
                denominator = look_dist_ft
            else:
                denominator = look_dist_ft * (1 + sensitivity)
            
            if fabs(denominator) > 1e-9:
                correction = -height_diff_ft / denominator
            else:
                # Restore original constraints before raising error
                if has_restore_cMaximumDrop:
                    self._config_s.cMaximumDrop = restore_cMaximumDrop
                if has_restore_cMinimumAltitude:
                    self._config_s.cMinimumAltitude = restore_cMinimumAltitude
                raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>self._shot_s.barrel_elevation),
                                     'Correction denominator is zero')

            if range_error_ft > ALLOWED_ZERO_ERROR_FEET:
                # We're still trying to reach zero_distance
                if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                    # Restore original constraints before raising error
                    if has_restore_cMaximumDrop:
                        self._config_s.cMaximumDrop = restore_cMaximumDrop
                    if has_restore_cMinimumAltitude:
                        self._config_s.cMinimumAltitude = restore_cMinimumAltitude
                    raise ZeroFindingError(range_error_ft, iterations_count, _new_rad(<double>self._shot_s.barrel_elevation),
                                         'Distance non-convergent')
            elif height_error_ft > fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                if damping_factor < 0.3:
                    # Restore original constraints before raising error
                    if has_restore_cMaximumDrop:
                        self._config_s.cMaximumDrop = restore_cMaximumDrop
                    if has_restore_cMinimumAltitude:
                        self._config_s.cMinimumAltitude = restore_cMinimumAltitude
                    raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>self._shot_s.barrel_elevation),
                                         'Error non-convergent')
                # Revert previous adjustment
                self._shot_s.barrel_elevation -= last_correction
                correction = last_correction
            elif damping_factor < 1.0:
                damping_factor = 1.0

            prev_range_error_ft = range_error_ft
            prev_height_error_ft = height_error_ft

            if height_error_ft > _cZeroFindingAccuracy or range_error_ft > ALLOWED_ZERO_ERROR_FEET:
                # Adjust barrel elevation to close height at zero distance
                applied_correction = correction * damping_factor
                self._shot_s.barrel_elevation += applied_correction
                last_correction = applied_correction
            else:  # Current barrel_elevation hit zero: success!
                break
            
            iterations_count += 1

        # Restore original constraints
        if has_restore_cMaximumDrop:
            self._config_s.cMaximumDrop = restore_cMaximumDrop
        if has_restore_cMinimumAltitude:
            self._config_s.cMinimumAltitude = restore_cMinimumAltitude

        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(<double>self._shot_s.barrel_elevation))
        
        return _new_rad(<double>self._shot_s.barrel_elevation)


    cdef object _integrate(CythonizedBaseIntegrationEngine self,
                           double range_limit_ft, double range_step_ft,
                           double time_step, int filter_flags, bint dense_output):
        raise NotImplementedError


cdef object create_trajectory_row(double time, const V3dT *range_vector_ptr, const V3dT *velocity_vector_ptr,
                                  double mach, const ShotData_t *shot_data_ptr,
                                  double density_ratio, double drag, int flag):

    cdef:
        double look_angle = shot_data_ptr.look_angle
        double spin_drift = ShotData_t_spinDrift(shot_data_ptr, time)
        double velocity = mag(velocity_vector_ptr)
        double windage = range_vector_ptr.z + spin_drift
        double drop_adjustment = getCorrection(range_vector_ptr.x, range_vector_ptr.y)
        double windage_adjustment = getCorrection(range_vector_ptr.x, windage)
        double trajectory_angle = atan2(velocity_vector_ptr.y, velocity_vector_ptr.x);
        double look_angle_cos = cos(look_angle)
        double look_angle_sin = sin(look_angle)

    drop_adjustment -= (look_angle if range_vector_ptr.x else 0)

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector_ptr.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector_ptr.y),
        slant_height=_new_feet(range_vector_ptr.y * look_angle_cos - range_vector_ptr.x * look_angle_sin),
        drop_adj=_new_rad(drop_adjustment),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        slant_distance=_new_feet(range_vector_ptr.x * look_angle_cos + range_vector_ptr.y * look_angle_sin),
        angle=_new_rad(trajectory_angle),
        density_ratio=density_ratio,
        drag=drag,
        energy=_new_ft_lb(calculateEnergy(shot_data_ptr.weight, velocity)),
        ogw=_new_lb(calculateOgw(shot_data_ptr.weight, velocity)),
        flag=flag
    )


cdef object _new_feet(double v):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


cdef object _new_fps(double v):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


cdef object _new_rad(double v):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


cdef object _new_ft_lb(double v):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


cdef object _new_lb(double v):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d