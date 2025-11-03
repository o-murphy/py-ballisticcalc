#include <math.h>
#include "bclibc_euler.h"
// #include "bclibc_bclib.h"  // for C_LOG

/**
 * @brief Calculate time step based on current projectile speed.
 * @param base_step The base time step value.
 * @param velocity The current projectile speed (magnitude of velocity).
 * @return double The calculated time step.
 */
static inline double BCLIBC_euler_time_step(double base_step, double velocity)
{
    // C equivalent of fmax(1.0, velocity)
    // fmax is defined in <math.h>
    double divisor = velocity > 1.0 ? velocity : 1.0;
    return base_step / divisor;
}

/**
 * @brief Performs trajectory simulation using the Euler integration method.
 * * This function calculates the projectile's trajectory, updating its position
 * and velocity step-by-step until a termination condition is met (e.g., max
 * range, minimum velocity, or max drop). It accounts for gravity, drag (using
 * Mach number), wind, and Coriolis effects.
 *
 * @param shot_props_ptr Pointer to the BCLIBC_ShotProps structure containing
 * muzzle conditions, drag curve, and atmospheric data.
 * @param wind_sock_ptr Pointer to the BCLIBC_WindSock structure for wind interpolation.
 * @param config_ptr Pointer to the global configuration constants (e.g., gravity).
 * @param range_limit_ft The maximum horizontal range (in feet) to simulate.
 * @param range_step_ft The distance step for recording trajectory points
 * (not used for integration step size).
 * @param time_step The base time step for integration (can be adaptive).
 * @param filter_flags Flags (BCLIBC_TrajFlag) specifying additional points to record.
 * @param traj_seq_ptr Pointer to the BCLIBC_BaseTrajSeq buffer where trajectory
 * data points will be stored.
 * @return BCLIBC_ErrorType An enumeration value indicating why the integration
 * loop was terminated (e.g., NO_ERROR on success).
 */
BCLIBC_StatusCode BCLIBC_integrateEULER(
    BCLIBC_EngineT *eng,
    double range_limit_ft, double range_step_ft,
    double time_step, BCLIBC_TrajFlag filter_flags,
    BCLIBC_BaseTrajSeq *traj_seq_ptr,
    BCLIBC_TerminationReason *reason)
{
    if (!eng || !traj_seq_ptr || !reason)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_INTEGRATE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    double velocity, delta_time;
    double density_ratio = 0.0;
    double mach = 0.0;
    double time = 0.0;
    double drag = 0.0;
    double km = 0.0;
    BCLIBC_V3dT range_vector;
    BCLIBC_V3dT velocity_vector;
    BCLIBC_V3dT relative_velocity;
    BCLIBC_V3dT gravity_vector;
    BCLIBC_V3dT wind_vector;
    BCLIBC_V3dT coriolis_accel;
    double calc_step = eng->shot.calc_step;

    // Early binding of configuration constants
    double _cMinimumVelocity = eng->config.cMinimumVelocity;
    double _cMinimumAltitude = eng->config.cMinimumAltitude;
    double _cMaximumDrop = -fabs(eng->config.cMaximumDrop);

    // Working variables
    *reason = BCLIBC_TERM_REASON_NO_TERMINATE;
    double relative_speed;
    BCLIBC_V3dT _dir_vector;
    BCLIBC_V3dT _tv;
    BCLIBC_V3dT delta_range_vector;
    eng->integration_step_count = 0;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = eng->config.cGravityConstant;
    gravity_vector.z = 0.0;

    // Initialize wind vector
    wind_vector = BCLIBC_WindSock_currentVector(&eng->shot.wind_sock);

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
    velocity_vector = BCLIBC_V3dT_mulS(&_dir_vector, velocity);

    // Trajectory Loop

    // Update air density and mach at initial altitude
    BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
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
            wind_vector = BCLIBC_WindSock_vectorForRange(&eng->shot.wind_sock, range_vector.x);
        }

        // Update air density and mach at current altitude
        BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
            &eng->shot.atmo,
            eng->shot.alt0 + range_vector.y,
            &density_ratio,
            &mach);

        // Store point in trajectory sequence

        // err =
        BCLIBC_BaseTrajSeq_append(
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
        relative_velocity = BCLIBC_V3dT_sub(&velocity_vector, &wind_vector);
        relative_speed = BCLIBC_V3dT_mag(&relative_velocity);

        // 2. Calculate time step (adaptive based on velocity)
        delta_time = BCLIBC_euler_time_step(calc_step, relative_speed);

        // 3. Calculate drag coefficient and drag force
        km = density_ratio * BCLIBC_ShotProps_dragByMach(&eng->shot, relative_speed / mach);
        drag = km * relative_speed;

        // 4. Apply drag, gravity, and Coriolis to velocity
        _tv = BCLIBC_V3dT_mulS(&relative_velocity, drag);
        _tv = BCLIBC_V3dT_sub(&gravity_vector, &_tv);

        // Check the flat_fire_only flag within the Coriolis structure
        if (!eng->shot.coriolis.flat_fire_only)
        {
            BCLIBC_Coriolis_coriolisAccelerationLocal(
                &eng->shot.coriolis, &velocity_vector, &coriolis_accel);
            _tv = BCLIBC_V3dT_add(&_tv, &coriolis_accel);
        }

        _tv = BCLIBC_V3dT_mulS(&_tv, delta_time);
        velocity_vector = BCLIBC_V3dT_add(&velocity_vector, &_tv);

        // 5. Update position based on new velocity
        delta_range_vector = BCLIBC_V3dT_mulS(&velocity_vector, delta_time);
        range_vector = BCLIBC_V3dT_add(&range_vector, &delta_range_vector);

        // 6. Update time and velocity magnitude
        velocity = BCLIBC_V3dT_mag(&velocity_vector);
        time += delta_time;

        // Check termination conditions
        if (velocity < _cMinimumVelocity)
        {
            *reason = BCLIBC_TERM_REASON_MINIMUM_VELOCITY_REACHED;
        }
        else if (range_vector.y < _cMaximumDrop)
        {
            *reason = BCLIBC_TERM_REASON_MAXIMUM_DROP_REACHED;
        }
        else if (velocity_vector.y <= 0 && (eng->shot.alt0 + range_vector.y < _cMinimumAltitude))
        {
            *reason = BCLIBC_TERM_REASON_MINIMUM_ALTITUDE_REACHED;
        }

        if (*reason != BCLIBC_TERM_REASON_NO_TERMINATE)
        {
            break;
        }
    }

    // Add final data point

    // err =
    BCLIBC_BaseTrajSeq_append(
        traj_seq_ptr,
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach);
    // if (err != NO_ERROR)
    // {
    //     return err;
    // }

    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Function exit, reason=%d\n", *reason);

    return BCLIBC_STATUS_SUCCESS;
}
