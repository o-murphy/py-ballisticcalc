#include <math.h>
#include "euler.h"
// #include "bclib.h"  // for C_LOG

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
 * @return ErrorCode An enumeration value indicating why the integration
 * loop was terminated (e.g., NO_ERROR on success).
 */
StatusCode _integrate_euler(
    Engine_t *eng,
    double range_limit_ft, double range_step_ft,
    double time_step, TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr,
    TerminationReason *reason)
{

    if (!eng || !traj_seq_ptr || !reason)
    {
        return Engine_t_LOG_AND_SAVE_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
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
    double calc_step = eng->shot.calc_step;

    // Early binding of configuration constants
    double _cMinimumVelocity = eng->config.cMinimumVelocity;
    double _cMinimumAltitude = eng->config.cMinimumAltitude;
    double _cMaximumDrop = -fabs(eng->config.cMaximumDrop);

    // Working variables
    *reason = NO_TERMINATE;
    double relative_speed;
    V3dT _dir_vector;
    V3dT _tv;
    V3dT delta_range_vector;
    eng->integration_step_count = 0;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = eng->config.cGravityConstant;
    gravity_vector.z = 0.0;

    // Initialize wind vector
    wind_vector = WindSock_t_currentVector(&eng->shot.wind_sock);

    // Initialize velocity and position vectors
    velocity = eng->shot.muzzle_velocity;

    // Set range_vector components
    range_vector.x = 0.0;
    range_vector.y = -eng->shot.cant_cosine * eng->shot.sight_height;
    range_vector.z = -eng->shot.cant_sine * eng->shot.sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y); // Adjust max drop downward (only) for muzzle height

    // Set direction vector components
    _dir_vector.x = cos(eng->shot.barrel_elevation) * cos(eng->shot.barrel_azimuth);
    _dir_vector.y = sin(eng->shot.barrel_elevation);
    _dir_vector.z = cos(eng->shot.barrel_elevation) * sin(eng->shot.barrel_azimuth);

    // Calculate velocity vector
    velocity_vector = mulS(&_dir_vector, velocity);

    // Trajectory Loop

    // Update air density and mach at initial altitude
    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &eng->shot.atmo,
        eng->shot.alt0 + range_vector.y,
        &density_ratio,
        &mach);

    // Cubic interpolation requires 3 points, so we will need at least 3 steps
    while (range_vector.x <= range_limit_ft || eng->integration_step_count < 3)
    {
        eng->integration_step_count++;

        // Update wind reading at current point in trajectory
        if (range_vector.x >= eng->shot.wind_sock.next_range)
        {
            wind_vector = WindSock_t_vectorForRange(&eng->shot.wind_sock, range_vector.x);
        }

        // Update air density and mach at current altitude
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &eng->shot.atmo,
            eng->shot.alt0 + range_vector.y,
            &density_ratio,
            &mach);

        // Store point in trajectory sequence

        // err =
        BaseTrajSeq_t_append(
            traj_seq_ptr,
            time,
            range_vector.x, range_vector.y, range_vector.z,
            velocity_vector.x, velocity_vector.y, velocity_vector.z,
            mach);
        // if (err != NO_ERROR)
        // {
        //     return err;
        // }

        // Euler integration step

        // 1. Calculate relative velocity (projectile velocity - wind)
        relative_velocity = sub(&velocity_vector, &wind_vector);
        relative_speed = mag(&relative_velocity);

        // 2. Calculate time step (adaptive based on velocity)
        delta_time = _euler_time_step(calc_step, relative_speed);

        // 3. Calculate drag coefficient and drag force
        km = density_ratio * ShotProps_t_dragByMach(&eng->shot, relative_speed / mach);
        drag = km * relative_speed;

        // 4. Apply drag, gravity, and Coriolis to velocity
        _tv = mulS(&relative_velocity, drag);
        _tv = sub(&gravity_vector, &_tv);

        // Check the flat_fire_only flag within the Coriolis structure
        if (!eng->shot.coriolis.flat_fire_only)
        {
            Coriolis_t_coriolis_acceleration_local(
                &eng->shot.coriolis, &velocity_vector, &coriolis_accel);
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
            *reason = RANGE_ERROR_MINIMUM_VELOCITY_REACHED;
        }
        else if (velocity_vector.y <= 0 && range_vector.y < _cMaximumDrop)
        {
            *reason = RANGE_ERROR_MAXIMUM_DROP_REACHED;
        }
        else if (velocity_vector.y <= 0 && (eng->shot.alt0 + range_vector.y < _cMinimumAltitude))
        {
            *reason = RANGE_ERROR_MINIMUM_ALTITUDE_REACHED;
        }

        if (*reason != NO_TERMINATE)
        {
            break;
        }
    }

    // Add final data point

    // err =
    BaseTrajSeq_t_append(
        traj_seq_ptr,
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach);
    // if (err != NO_ERROR)
    // {
    //     return err;
    // }

    C_LOG(LOG_LEVEL_DEBUG, "Function exit, reason=%d\n", *reason);

    return STATUS_SUCCESS;
}
