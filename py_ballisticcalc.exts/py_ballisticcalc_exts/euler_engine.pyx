"""
Cythonized Euler Integration Engine

Because storing each step in a CBaseTrajSeq is practically costless, we always run with "dense_output=True".
"""
from cython cimport final
from libc.math cimport fabs, sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    ShotProps_t,
    Config_t,
    ShotProps_t_dragByMach,
    Atmosphere_t_updateDensityFactorAndMachForAltitude,
    Coriolis_t_coriolis_acceleration_local,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    WindSock_t,
    WindSock_t_currentVector,
    WindSock_t_vectorForRange,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT, add, sub, mag, mulS
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport CBaseTrajSeq

import warnings

from py_ballisticcalc.exceptions import RangeError

__all__ = [
    'CythonizedEulerIntegrationEngine',
]

cdef extern from "include/euler.h":
    double _euler_time_step(double base_step, double velocity) noexcept nogil


@final
cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""
    DEFAULT_STEP = 0.5  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    cdef double get_calc_step(CythonizedEulerIntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)

    cdef tuple _integrate(CythonizedEulerIntegrationEngine self, ShotProps_t *shot_props_ptr,
                           double range_limit_ft, double range_step_ft,
                           double time_step, int filter_flags):
        return _integrate_euler(
            shot_props_ptr,
            self._wind_sock,
            &self._config_s,
            range_limit_ft, 
            range_step_ft, 
            time_step, 
            filter_flags
        )

cdef tuple _integrate_euler(ShotProps_t *shot_props_ptr,
                            WindSock_t *wind_sock_ptr,
                            const Config_t *config_ptr,
                            double range_limit_ft, double range_step_ft,
                            double time_step, int filter_flags):
    """
    Creates trajectory data for the specified shot using Euler integration.
    
    Args:
        range_limit_ft: Maximum range in feet
        range_step_ft: Distance step for recording points
        time_step: Time step for recording points
        filter_flags: Flags for special points to record
    
    Returns:
        Tuple of (list of TrajectoryData points, optional error) or
        (CBaseTrajSeq, optional error) if dense_output is True
    """
    cdef:
        double velocity
        double delta_time
        double density_ratio = <double>0.0
        double mach = <double>0.0
        CBaseTrajSeq traj_seq
        double time = <double>0.0
        double drag = <double>0.0
        double km = <double>0.0
        V3dT range_vector
        V3dT velocity_vector
        V3dT relative_velocity
        V3dT gravity_vector
        V3dT wind_vector
        V3dT coriolis_accel
        double calc_step = shot_props_ptr.calc_step
        
        # Early binding of configuration constants
        double _cMinimumVelocity = config_ptr.cMinimumVelocity
        double _cMinimumAltitude = config_ptr.cMinimumAltitude
        double _cMaximumDrop = -fabs(config_ptr.cMaximumDrop)
        
        # Working variables
        object termination_reason = None
        double relative_speed
        V3dT _dir_vector
        V3dT _tv
        V3dT delta_range_vector
        int integration_step_count = 0

    # Initialize gravity vector
    gravity_vector.x = <double>0.0
    gravity_vector.y = config_ptr.cGravityConstant
    gravity_vector.z = <double>0.0

    # Initialize wind vector
    wind_vector = WindSock_t_currentVector(wind_sock_ptr)

    # Initialize velocity and position vectors
    velocity = shot_props_ptr.muzzle_velocity
    
    # Set range_vector components
    range_vector.x = <double>0.0
    range_vector.y = -shot_props_ptr.cant_cosine * shot_props_ptr.sight_height
    range_vector.z = -shot_props_ptr.cant_sine * shot_props_ptr.sight_height
    _cMaximumDrop += fmin(<double>0.0, range_vector.y)  # Adjust max drop downward (only) for muzzle height
    
    # Set direction vector components
    _dir_vector.x = cos(shot_props_ptr.barrel_elevation) * cos(shot_props_ptr.barrel_azimuth)
    _dir_vector.y = sin(shot_props_ptr.barrel_elevation)
    _dir_vector.z = cos(shot_props_ptr.barrel_elevation) * sin(shot_props_ptr.barrel_azimuth)
    
    # Calculate velocity vector
    velocity_vector = mulS(&_dir_vector, velocity)

    # Initialize trajectory sequence for dense output if needed
    traj_seq = CBaseTrajSeq()

    # Trajectory Loop
    warnings.simplefilter("once")  # avoid multiple warnings
    
    # Update air density and mach at initial altitude
    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &shot_props_ptr.atmo,
        shot_props_ptr.alt0 + range_vector.y,
        &density_ratio,
        &mach
    )

    # Cubic interpolation requires 3 points, so we will need at least 3 steps
    while (range_vector.x <= range_limit_ft) or integration_step_count < 3:
        integration_step_count += 1

        # Update wind reading at current point in trajectory
        if range_vector.x >= wind_sock_ptr.next_range:
            wind_vector = WindSock_t_vectorForRange(wind_sock_ptr, range_vector.x)

        # Update air density and mach at current altitude
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &shot_props_ptr.atmo,
            shot_props_ptr.alt0 + range_vector.y,
            &density_ratio,
            &mach
        )

        # Store point in trajectory sequence
        traj_seq._append_c(time, range_vector.x, range_vector.y, range_vector.z,
                        velocity_vector.x, velocity_vector.y, velocity_vector.z, mach)
        
        # Euler integration step
        
        # 1. Calculate relative velocity (projectile velocity - wind)
        relative_velocity = sub(&velocity_vector, &wind_vector)
        relative_speed = mag(&relative_velocity)
        
        # 2. Calculate time step (adaptive based on velocity)
        delta_time = _euler_time_step(calc_step, relative_speed)
        
        # 3. Calculate drag coefficient and drag force
        km = density_ratio * ShotProps_t_dragByMach(shot_props_ptr, relative_speed / mach)
        drag = km * relative_speed
        
        # 4. Apply drag, gravity, and Coriolis to velocity
        _tv = mulS(&relative_velocity, drag)
        _tv = sub(&gravity_vector, &_tv)
        
        # Add Coriolis acceleration if available
        if not shot_props_ptr.coriolis.flat_fire_only:
            Coriolis_t_coriolis_acceleration_local(&shot_props_ptr.coriolis, &velocity_vector, &coriolis_accel)
            _tv = add(&_tv, &coriolis_accel)
        
        _tv = mulS(&_tv, delta_time)
        velocity_vector = add(&velocity_vector, &_tv)
        
        # 5. Update position based on new velocity
        delta_range_vector = mulS(&velocity_vector, delta_time)
        range_vector = add(&range_vector, &delta_range_vector)
        
        # 6. Update time and velocity magnitude
        velocity = mag(&velocity_vector)
        time += delta_time

        # Check termination conditions
        if (velocity < _cMinimumVelocity
            or (velocity_vector.y <= 0 and range_vector.y < _cMaximumDrop)
            or (velocity_vector.y <= 0 and shot_props_ptr.alt0 + range_vector.y < _cMinimumAltitude)
        ):
            if velocity < _cMinimumVelocity:
                termination_reason = RangeError.MinimumVelocityReached
            elif range_vector.y < _cMaximumDrop:
                termination_reason = RangeError.MaximumDropReached
            else:
                termination_reason = RangeError.MinimumAltitudeReached
            break
    # Add final data point
    traj_seq._append_c(
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach
    )
    return (traj_seq, termination_reason)
