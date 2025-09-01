"""
Cythonized RK4 Integration Engine

Because storing each step in a CBaseTrajSeq is practically costless, we always run with "dense_output=True".
"""
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    ShotProps_t,
    ShotProps_t_dragByMach,
    Atmosphere_t_updateDensityFactorAndMachForAltitude,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    WindSock_t_currentVector,
    WindSock_t_vectorForRange,
)
from py_ballisticcalc_exts.base_traj_seq cimport CBaseTrajSeq
from py_ballisticcalc_exts.v3d cimport V3dT, add, sub, mag, mulS

from py_ballisticcalc.exceptions import RangeError

__all__ = [
    'CythonizedRK4IntegrationEngine',
]

@final
cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""
    DEFAULT_TIME_STEP = 0.0025

    cdef double get_calc_step(CythonizedRK4IntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_TIME_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)

    cdef tuple _integrate(CythonizedRK4IntegrationEngine self, ShotProps_t *shot_props_ptr,
                           double range_limit_ft, double range_step_ft,
                           double time_step, int filter_flags):
        """
        Creates trajectory data for the specified shot using RK4 integration.
        
        Args:
            range_limit_ft: Maximum range in feet
            range_step_ft: Distance step for recording points
            time_step: Time step for recording points
            filter_flags: Flags for special points to record
        
        Returns:
            (CBaseTrajSeq, optional error)

        """
        cdef:
            double velocity, delta_time
            double density_ratio = <double>0.0
            double mach = <double>0.0
            double time = <double>0.0
            double km = <double>0.0
            V3dT range_vector
            V3dT velocity_vector
            V3dT relative_velocity
            V3dT gravity_vector
            V3dT wind_vector
            double calc_step
            
            # Early binding of configuration constants
            double _cMinimumVelocity = self._config_s.cMinimumVelocity
            double _cMinimumAltitude = self._config_s.cMinimumAltitude
            double _cMaximumDrop = -abs(self._config_s.cMaximumDrop)
            
            # Working variables
            object termination_reason = None
            double relative_speed
            V3dT _dir_vector
            int integration_step_count = 0
            
            # RK4 specific variables
            V3dT _temp_add_operand
            V3dT _temp_v_result
            V3dT _v_sum_intermediate
            V3dT _p_sum_intermediate
            V3dT v1, v2, v3, v4
            V3dT p1, p2, p3, p4
            
            # For storing dense output
            CBaseTrajSeq traj_seq

        # Initialize gravity vector
        gravity_vector.x = <double>0.0
        gravity_vector.y = self._config_s.cGravityConstant
        gravity_vector.z = <double>0.0

        # Initialize wind vector
        wind_vector = WindSock_t_currentVector(self._wind_sock)

        # Initialize velocity and position vectors
        velocity = shot_props_ptr[0].muzzle_velocity
        calc_step = shot_props_ptr[0].calc_step
        
        # Set range_vector components directly
        range_vector.x = <double>0.0
        range_vector.y = -shot_props_ptr[0].cant_cosine * shot_props_ptr[0].sight_height
        range_vector.z = -shot_props_ptr[0].cant_sine * shot_props_ptr[0].sight_height
        _cMaximumDrop += fmin(<double>0.0, range_vector.y)  # Adjust max drop downward (only) for muzzle height
        
        # Set direction vector components
        _dir_vector.x = cos(shot_props_ptr[0].barrel_elevation) * cos(shot_props_ptr[0].barrel_azimuth)
        _dir_vector.y = sin(shot_props_ptr[0].barrel_elevation)
        _dir_vector.z = cos(shot_props_ptr[0].barrel_elevation) * sin(shot_props_ptr[0].barrel_azimuth)
        
        # Calculate velocity vector
        velocity_vector = mulS(&_dir_vector, velocity)

        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &shot_props_ptr[0].atmo,
            shot_props_ptr[0].alt0 + range_vector.y,
            &density_ratio,
            &mach
        )
        
        traj_seq = CBaseTrajSeq()

        # Trajectory Loop
        # Cubic interpolation requires 3 points, so we will need at least 3 steps
        while (range_vector.x <= range_limit_ft) or integration_step_count < 3:
            integration_step_count += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= self._wind_sock.next_range:
                wind_vector = WindSock_t_vectorForRange(self._wind_sock, range_vector.x)

            # Update air density and mach at current altitude
            Atmosphere_t_updateDensityFactorAndMachForAltitude(
                &shot_props_ptr[0].atmo,
                shot_props_ptr[0].alt0 + range_vector.y,
                &density_ratio,
                &mach
            )

            # Store point in trajectory sequence
            traj_seq.append(
                time,
                range_vector.x, range_vector.y, range_vector.z,
                velocity_vector.x, velocity_vector.y, velocity_vector.z,
                mach
            )
            
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            relative_velocity = sub(&velocity_vector, &wind_vector)
            relative_speed = mag(&relative_velocity)

            delta_time = calc_step
            km = density_ratio * ShotProps_t_dragByMach(shot_props_ptr, relative_speed / mach)

            #region RK4 integration
            
            # v1 = f(relative_velocity)
            v1 = _calculate_dvdt(&relative_velocity, &gravity_vector, km)

            # v2 = f(relative_velocity + 0.5 * delta_time * v1)
            _temp_add_operand = mulS(&v1, 0.5 * delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v2 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km)

            # v3 = f(relative_velocity + 0.5 * delta_time * v2)
            _temp_add_operand = mulS(&v2, 0.5 * delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v3 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km)

            # v4 = f(relative_velocity + delta_time * v3)
            _temp_add_operand = mulS(&v3, delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v4 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km)

            # p1 = velocity_vector
            p1 = velocity_vector

            # p2 = (velocity_vector + 0.5 * delta_time * v1)
            _temp_add_operand = mulS(&v1, 0.5 * delta_time)
            p2 = add(&velocity_vector, &_temp_add_operand)

            # p3 = (velocity_vector + 0.5 * delta_time * v2)
            _temp_add_operand = mulS(&v2, 0.5 * delta_time)
            p3 = add(&velocity_vector, &_temp_add_operand)

            # p4 = (velocity_vector + delta_time * v3)
            _temp_add_operand = mulS(&v3, delta_time)
            p4 = add(&velocity_vector, &_temp_add_operand)

            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)
            _temp_add_operand = mulS(&v2, <double>2.0)
            _v_sum_intermediate = add(&v1, &_temp_add_operand)
            _temp_add_operand = mulS(&v3, <double>2.0)
            _v_sum_intermediate = add(&_v_sum_intermediate, &_temp_add_operand)
            _v_sum_intermediate = add(&_v_sum_intermediate, &v4)
            _v_sum_intermediate = mulS(&_v_sum_intermediate, (delta_time / <double>6.0))
            velocity_vector = add(&velocity_vector, &_v_sum_intermediate)

            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)
            _temp_add_operand = mulS(&p2, <double>2.0)
            _p_sum_intermediate = add(&p1, &_temp_add_operand)
            _temp_add_operand = mulS(&p3, <double>2.0)
            _p_sum_intermediate = add(&_p_sum_intermediate, &_temp_add_operand)
            _p_sum_intermediate = add(&_p_sum_intermediate, &p4)
            _p_sum_intermediate = mulS(&_p_sum_intermediate, (delta_time / <double>6.0))
            range_vector = add(&range_vector, &_p_sum_intermediate)
            
            # Update time and velocity magnitude
            velocity = mag(&velocity_vector)
            time += delta_time
            
            # Check termination conditions
            if (velocity < _cMinimumVelocity
                or (velocity_vector.y <= 0 and range_vector.y < _cMaximumDrop)
                or (velocity_vector.y <= 0 and shot_props_ptr[0].alt0 + range_vector.y < _cMinimumAltitude)
            ):
                if velocity < _cMinimumVelocity:
                    termination_reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    termination_reason = RangeError.MaximumDropReached
                else:
                    termination_reason = RangeError.MinimumAltitudeReached
                break
            #endregion
        # Process final data point
        traj_seq.append(
            time,
            range_vector.x, range_vector.y, range_vector.z,
            velocity_vector.x, velocity_vector.y, velocity_vector.z,
            mach
        )
        return (traj_seq, termination_reason)
        
        
# This function calculates dv/dt for velocity (v) affected by gravity and drag.
cdef V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff):
    """Calculate the derivative of velocity with respect to time.
    
    Args:
        v_ptr: Pointer to the velocity vector
        gravity_vector_ptr: Pointer to the gravity vector
        km_coeff: Drag coefficient
        
    Returns:
        The acceleration vector (dv/dt)
    """
    cdef V3dT drag_force_component
    # Bullet velocity changes due to both drag and gravity
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    return sub(gravity_vector_ptr, &drag_force_component)
