#include <math.h>
#include "euler.h"
// #include <stdio.h>  // for printf (DEBUG)

/**
 * @brief Calculate time step based on current projectile speed.
 * * @param base_step The base time step value.
 * @param velocity The current projectile speed (magnitude of velocity).
 * @return double The calculated time step.
 */
double _euler_time_step(double base_step, double velocity)
{
    // C equivalent of fmax(1.0, velocity)
    // fmax is defined in <math.h>
    double divisor = fmax(1.0, velocity);

    return base_step / divisor;
}

/**
 * @brief Performs trajectory simulation using the Euler integration method.
 * * This function calculates the projectile's trajectory, updating its position
 * and velocity step-by-step until a termination condition is met (e.g., max
 * range, minimum velocity, or max drop). It accounts for gravity, drag (using
 * Mach number), wind, and Coriolis effects.
 *
 * @param shot_props_ptr Pointer to the ShotProps_t structure containing
 * muzzle conditions, drag curve, and atmospheric data.
 * @param wind_sock_ptr Pointer to the WindSock_t structure for wind interpolation.
 * @param config_ptr Pointer to the global configuration constants (e.g., gravity).
 * @param range_limit_ft The maximum horizontal range (in feet) to simulate.
 * @param range_step_ft The distance step for recording trajectory points
 * (not used for integration step size).
 * @param time_step The base time step for integration (can be adaptive).
 * @param filter_flags Flags (TrajFlag_t) specifying additional points to record.
 * @param traj_seq_ptr Pointer to the BaseTrajSeq_t buffer where trajectory
 * data points will be stored.
 * @return TerminationReason An enumeration value indicating why the integration
 * loop was terminated (e.g., NoRangeError on success).
 */
TerminationReason _integrate_euler(const ShotProps_t *shot_props_ptr,
                                   WindSock_t *wind_sock_ptr,
                                   const Config_t *config_ptr,
                                   double range_limit_ft, double range_step_ft,
                                   double time_step, int filter_flags,
                                   BaseTrajSeq_t *traj_seq_ptr)
{

    if (!shot_props_ptr)
    {
        // printf("ERROR: shot_props_ptr is NULL\n");
        return RangeErrorInvalidParameter;
    }
    if (!wind_sock_ptr)
    {
        // printf("ERROR: wind_sock_ptr is NULL\n");
        return RangeErrorInvalidParameter;
    }
    if (!config_ptr)
    {
        // printf("ERROR: config_ptr is NULL\n");
        return RangeErrorInvalidParameter;
    }
    if (!traj_seq_ptr)
    {
        // printf("ERROR: traj_seq_ptr is NULL\n");
        return RangeErrorInvalidParameter;
    }

    double velocity, delta_time;
    double density_ratio = 0.0;
    double mach = 0.0;
    double time = 0.0;
    double drag = 0.0;
    double km = 0.0;
    V3dT range_vector;
    V3dT velocity_vector;
    V3dT relative_velocity;
    V3dT gravity_vector;
    V3dT wind_vector;
    V3dT coriolis_accel;
    double calc_step = shot_props_ptr->calc_step;

    // Early binding of configuration constants
    double _cMinimumVelocity = config_ptr->cMinimumVelocity;
    double _cMinimumAltitude = config_ptr->cMinimumAltitude;
    double _cMaximumDrop = -fabs(config_ptr->cMaximumDrop);

    // Working variables
    TerminationReason termination_reason = NoRangeError;
    double relative_speed;
    V3dT _dir_vector;
    V3dT _tv;
    V3dT delta_range_vector;
    int integration_step_count = 0;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = config_ptr->cGravityConstant;
    gravity_vector.z = 0.0;

    // Initialize wind vector
    wind_vector = WindSock_t_currentVector(wind_sock_ptr);

    // Initialize velocity and position vectors
    velocity = shot_props_ptr->muzzle_velocity;

    // Set range_vector components
    range_vector.x = 0.0;
    range_vector.y = -shot_props_ptr->cant_cosine * shot_props_ptr->sight_height;
    range_vector.z = -shot_props_ptr->cant_sine * shot_props_ptr->sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y); // Adjust max drop downward (only) for muzzle height

    // Set direction vector components
    _dir_vector.x = cos(shot_props_ptr->barrel_elevation) * cos(shot_props_ptr->barrel_azimuth);
    _dir_vector.y = sin(shot_props_ptr->barrel_elevation);
    _dir_vector.z = cos(shot_props_ptr->barrel_elevation) * sin(shot_props_ptr->barrel_azimuth);

    // Calculate velocity vector
    velocity_vector = mulS(&_dir_vector, velocity);

    // Trajectory Loop

    // Update air density and mach at initial altitude
    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &shot_props_ptr->atmo,
        shot_props_ptr->alt0 + range_vector.y,
        &density_ratio,
        &mach);

    // Cubic interpolation requires 3 points, so we will need at least 3 steps
    while (range_vector.x <= range_limit_ft || integration_step_count < 3)
    {
        integration_step_count++;

        // Update wind reading at current point in trajectory
        if (range_vector.x >= wind_sock_ptr->next_range)
        {
            wind_vector = WindSock_t_vectorForRange(wind_sock_ptr, range_vector.x);
        }

        // Update air density and mach at current altitude
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &shot_props_ptr->atmo,
            shot_props_ptr->alt0 + range_vector.y,
            &density_ratio,
            &mach);

        // Store point in trajectory sequence
        BaseTrajSeq_t_append(
            traj_seq_ptr,
            time,
            range_vector.x, range_vector.y, range_vector.z,
            velocity_vector.x, velocity_vector.y, velocity_vector.z,
            mach);

        // Euler integration step

        // 1. Calculate relative velocity (projectile velocity - wind)
        relative_velocity = sub(&velocity_vector, &wind_vector);
        relative_speed = mag(&relative_velocity);

        // 2. Calculate time step (adaptive based on velocity)
        delta_time = _euler_time_step(calc_step, relative_speed);

        // 3. Calculate drag coefficient and drag force
        km = density_ratio * ShotProps_t_dragByMach(shot_props_ptr, relative_speed / mach);
        drag = km * relative_speed;

        // 4. Apply drag, gravity, and Coriolis to velocity
        _tv = mulS(&relative_velocity, drag);
        _tv = sub(&gravity_vector, &_tv);

        // Check the flat_fire_only flag within the Coriolis structure
        if (!shot_props_ptr->coriolis.flat_fire_only)
        {
            Coriolis_t_coriolis_acceleration_local(
                &shot_props_ptr->coriolis, &velocity_vector, &coriolis_accel);
            _tv = add(&_tv, &coriolis_accel);
        }

        _tv = mulS(&_tv, delta_time);
        velocity_vector = add(&velocity_vector, &_tv);

        // 5. Update position based on new velocity
        delta_range_vector = mulS(&velocity_vector, delta_time);
        range_vector = add(&range_vector, &delta_range_vector);

        // 6. Update time and velocity magnitude
        velocity = mag(&velocity_vector);
        time += delta_time;

        // Check termination conditions
        if (velocity < _cMinimumVelocity)
        {
            termination_reason = RangeErrorMinimumVelocityReached;
        }
        else if (velocity_vector.y <= 0 && range_vector.y < _cMaximumDrop)
        {
            termination_reason = RangeErrorMaximumDropReached;
        }
        else if (velocity_vector.y <= 0 && (shot_props_ptr->alt0 + range_vector.y < _cMinimumAltitude))
        {
            termination_reason = RangeErrorMinimumAltitudeReached;
        }

        if (termination_reason != NoRangeError)
        {
            break;
        }
    }

    // Add final data point
    BaseTrajSeq_t_append(
        traj_seq_ptr,
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach);

    // printf("DEBUG: Function exit, reason=%d\n", termination_reason);
    // fflush(stdout);

    return termination_reason;
}