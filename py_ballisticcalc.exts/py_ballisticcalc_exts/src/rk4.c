#include <math.h>
#include "rk4.h"
#include "bclib.h"

/**
 * @brief Calculate the derivative of velocity with respect to time (acceleration).
 * * Assumes all necessary types (V3dT, ShotProps_t, Coriolis_t) and vector
 * functions (mulS, mag, sub, add, Coriolis_t_coriolis_acceleration_local)
 * are declared and defined in relevant C headers.
 *
 * @param v_ptr Pointer to the relative velocity vector (velocity - wind).
 * @param gravity_vector_ptr Pointer to the gravity vector.
 * @param km_coeff Drag coefficient.
 * @param shot_props_ptr Pointer to shot properties (for Coriolis data).
 * @param ground_velocity_ptr Pointer to ground velocity vector (for Coriolis calculation).
 * @return V3dT The acceleration vector (dv/dt).
 */
static inline V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff,
                                   const ShotProps_t *shot_props_ptr, const V3dT *ground_velocity_ptr)
{
    // Local variables for components and result
    V3dT drag_force_component;
    V3dT coriolis_acceleration;
    V3dT acceleration; // The return value

    // Bullet velocity changes due to drag and gravity
    // drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    // Note: Assuming mulS and mag operate on V3dT and double types respectively
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr));

    // acceleration = sub(gravity_vector_ptr, &drag_force_component)
    // Note: Assuming sub takes two const V3dT* and returns V3dT
    acceleration = sub(gravity_vector_ptr, &drag_force_component);

    // Add Coriolis acceleration if available
    // Check the flat_fire_only flag within the Coriolis structure
    if (!shot_props_ptr->coriolis.flat_fire_only)
    {
        // Coriolis_t_coriolis_acceleration_local(
        //     &shot_props_ptr->coriolis, ground_velocity_ptr, &coriolis_acceleration
        // )
        // Note: Assuming this function calculates Coriolis acceleration and stores it in the third argument
        Coriolis_t_coriolis_acceleration_local(
            &shot_props_ptr->coriolis, ground_velocity_ptr, &coriolis_acceleration);

        // acceleration = add(&acceleration, &coriolis_acceleration)
        // Note: Assuming add takes two const V3dT* and returns V3dT
        acceleration = add(&acceleration, &coriolis_acceleration);
    }

    return acceleration;
}

/**
 * @brief Performs trajectory simulation using the Fourth-order Runge-Kutta (RK4) method.
 *
 * This function calculates the projectile's trajectory, recording dense output
 * points until a termination condition is met (e.g., max range, min velocity,
 * or max drop). It integrates over time steps, accounting for gravity, drag,
 * wind, and Coriolis effects.
 *
 * @param shot_props_ptr Pointer to the ShotProps_t structure containing projectile
 * and atmospheric properties, and the drag curve.
 * @param wind_sock_ptr Pointer to the WindSock_t structure used for wind interpolation
 * along the trajectory.
 * @param config_ptr Pointer to the global Config_t structure holding constant parameters
 * (e.g., gravity constant, termination thresholds).
 * @param range_limit_ft The maximum horizontal range (in feet) to simulate.
 * @param range_step_ft The distance interval for recording filtered points (not used
 * for the integration step size).
 * @param time_step The base time step (dt) used for the RK4 calculation.
 * @param filter_flags Flags (TrajFlag_t) specifying special points to record
 * (e.g., ZERO, MACH, APEX).
 * @param traj_seq_ptr Pointer to the BaseTrajSeq_t buffer where dense trajectory
 * data points will be stored.
 * @return ErrorType An enumeration value indicating why the integration
 * loop was terminated (e.g., NO_ERROR on successful completion).
 */
StatusCode _integrate_rk4(
    Engine_t *eng,
    double range_limit_ft, double range_step_ft,
    double time_step, TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr,
    TerminationReason *reason)
{
    if (!eng || !traj_seq_ptr || !reason)
    {
        REQUIRE_NON_NULL(eng);
        PUSH_ERR(&eng->err_stack, T_INPUT_ERROR, SRC_INTEGRATE, "Invalid input (NULL pointer).");
        return STATUS_ERROR;
    };

    double velocity, delta_time;
    double density_ratio = 0.0;
    double mach = 0.0;
    double time = 0.0;
    double km = 0.0;
    V3dT range_vector;
    V3dT velocity_vector;
    V3dT relative_velocity;
    V3dT gravity_vector;
    V3dT wind_vector;
    double calc_step;

    C_LOG(LOG_LEVEL_DEBUG, "Variables declared\n");

    // Early binding of configuration constants
    double _cMinimumVelocity = eng->config.cMinimumVelocity;
    double _cMinimumAltitude = eng->config.cMinimumAltitude;
    double _cMaximumDrop = -fabs(eng->config.cMaximumDrop);

    C_LOG(LOG_LEVEL_DEBUG, "Config values read: minVel=%f, minAlt=%f, maxDrop=%f\n",
          _cMinimumVelocity, _cMinimumAltitude, _cMaximumDrop);

    // Working variables
    *reason = NO_TERMINATE;
    double relative_speed;
    V3dT _dir_vector;
    eng->integration_step_count = 0;

    // RK4 specific variables
    V3dT _temp_add_operand;
    V3dT _temp_v_result;
    V3dT _v_sum_intermediate;
    V3dT _p_sum_intermediate;
    V3dT v1, v2, v3, v4;
    V3dT p1, p2, p3, p4;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = eng->config.cGravityConstant;
    gravity_vector.z = 0.0;

    C_LOG(LOG_LEVEL_DEBUG, "Gravity initialized: %f\n", gravity_vector.y);

    // Initialize wind vector
    C_LOG(LOG_LEVEL_DEBUG, "About to call WindSock_t_currentVector\n");
    wind_vector = WindSock_t_currentVector(&eng->shot.wind_sock);
    C_LOG(LOG_LEVEL_DEBUG, "Wind vector: %f, %f, %f\n", wind_vector.x, wind_vector.y, wind_vector.z);

    // Initialize velocity and position vectors
    velocity = eng->shot.muzzle_velocity;
    calc_step = eng->shot.calc_step;

    C_LOG(LOG_LEVEL_DEBUG, "Velocity=%f, Calc Step=%f\n", velocity, calc_step);

    // Set range_vector components directly
    range_vector.x = 0.0;
    range_vector.y = -eng->shot.cant_cosine * eng->shot.sight_height;
    range_vector.z = -eng->shot.cant_sine * eng->shot.sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y);

    C_LOG(LOG_LEVEL_DEBUG, "Range vector: %f, %f, %f\n", range_vector.x, range_vector.y, range_vector.z);

    // Set direction vector components
    _dir_vector.x = cos(eng->shot.barrel_elevation) * cos(eng->shot.barrel_azimuth);
    _dir_vector.y = sin(eng->shot.barrel_elevation);
    _dir_vector.z = cos(eng->shot.barrel_elevation) * sin(eng->shot.barrel_azimuth);

    C_LOG(LOG_LEVEL_DEBUG, "Direction vector: %f, %f, %f\n", _dir_vector.x, _dir_vector.y, _dir_vector.z);

    // Calculate velocity vector
    C_LOG(LOG_LEVEL_DEBUG, "About to call mulS\n");
    velocity_vector = mulS(&_dir_vector, velocity);

    C_LOG(LOG_LEVEL_DEBUG, "Velocity vector: %f, %f, %f\n", velocity_vector.x, velocity_vector.y, velocity_vector.z);

    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &eng->shot.atmo,
        eng->shot.alt0 + range_vector.y,
        &density_ratio,
        &mach);
    C_LOG(LOG_LEVEL_DEBUG, "Density ratio: %f, Mach: %f\n", density_ratio, mach);

    // Trajectory Loop
    C_LOG(LOG_LEVEL_DEBUG, "Entering main loop, range_limit_ft=%f\n", range_limit_ft);

    while (range_vector.x <= range_limit_ft || eng->integration_step_count < 3)
    {
        C_LOG(LOG_LEVEL_DEBUG, "Loop iteration %d, range_x=%f\n", eng->integration_step_count, range_vector.x);

        eng->integration_step_count++;

        // Update wind reading at current point in trajectory
        if (range_vector.x >= eng->shot.wind_sock.next_range)
        {
            C_LOG(LOG_LEVEL_DEBUG, "Updating wind vector\n");
            wind_vector = WindSock_t_vectorForRange(&eng->shot.wind_sock, range_vector.x);
        }

        // Update air density and mach at current altitude
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &eng->shot.atmo,
            eng->shot.alt0 + range_vector.y,
            &density_ratio,
            &mach);

        // Store point in trajectory sequence
        C_LOG(LOG_LEVEL_DEBUG, "About to append to trajectory sequence\n");

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

        C_LOG(LOG_LEVEL_DEBUG, "Append successful\n");

        // Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = sub(&velocity_vector, &wind_vector);
        relative_speed = mag(&relative_velocity);

        delta_time = calc_step;

        C_LOG(LOG_LEVEL_DEBUG, "About to call ShotProps_t_dragByMach, relative_speed=%f, mach=%f\n",
              relative_speed, mach);

        // Check for division by zero
        // if (mach == 0.0)
        // {
        //     PUSH_ERR(&eng->err_stack, T_ZERO_DIVISION_ERROR, SRC_INTEGRATE, "Integration error: Mach number is zero cannot divide!");
        //     return STATUS_ERROR;
        // }

        km = density_ratio * ShotProps_t_dragByMach(&eng->shot, relative_speed / mach);
        C_LOG(LOG_LEVEL_DEBUG, "Calculated drag coefficient km=%f\n", km);

        // region RK4 integration
        C_LOG(LOG_LEVEL_DEBUG, "Starting RK4 integration\n");

        // v1 = f(relative_velocity)
        v1 = _calculate_dvdt(&relative_velocity, &gravity_vector, km, &eng->shot, &velocity_vector);

        // v2 = f(relative_velocity + 0.5 * delta_time * v1)
        _temp_add_operand = mulS(&v1, 0.5 * delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v2 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, &eng->shot, &velocity_vector);

        // v3 = f(relative_velocity + 0.5 * delta_time * v2)
        _temp_add_operand = mulS(&v2, 0.5 * delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v3 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, &eng->shot, &velocity_vector);

        // v4 = f(relative_velocity + delta_time * v3)
        _temp_add_operand = mulS(&v3, delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v4 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, &eng->shot, &velocity_vector);

        // p1 = velocity_vector
        p1 = velocity_vector;

        // p2 = (velocity_vector + 0.5 * delta_time * v1)
        _temp_add_operand = mulS(&v1, 0.5 * delta_time);
        p2 = add(&velocity_vector, &_temp_add_operand);

        // p3 = (velocity_vector + 0.5 * delta_time * v2)
        _temp_add_operand = mulS(&v2, 0.5 * delta_time);
        p3 = add(&velocity_vector, &_temp_add_operand);

        // p4 = (velocity_vector + delta_time * v3)
        _temp_add_operand = mulS(&v3, delta_time);
        p4 = add(&velocity_vector, &_temp_add_operand);

        // velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)
        _temp_add_operand = mulS(&v2, 2.0);
        _v_sum_intermediate = add(&v1, &_temp_add_operand);
        _temp_add_operand = mulS(&v3, 2.0);
        _v_sum_intermediate = add(&_v_sum_intermediate, &_temp_add_operand);
        _v_sum_intermediate = add(&_v_sum_intermediate, &v4);
        _v_sum_intermediate = mulS(&_v_sum_intermediate, (delta_time / 6.0));
        velocity_vector = add(&velocity_vector, &_v_sum_intermediate);

        // range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)
        _temp_add_operand = mulS(&p2, 2.0);
        _p_sum_intermediate = add(&p1, &_temp_add_operand);
        _temp_add_operand = mulS(&p3, 2.0);
        _p_sum_intermediate = add(&_p_sum_intermediate, &_temp_add_operand);
        _p_sum_intermediate = add(&_p_sum_intermediate, &p4);
        _p_sum_intermediate = mulS(&_p_sum_intermediate, (delta_time / 6.0));
        range_vector = add(&range_vector, &_p_sum_intermediate);

        C_LOG(LOG_LEVEL_DEBUG, "RK4 integration complete\n");

        // Update time and velocity magnitude
        velocity = mag(&velocity_vector);
        time += delta_time;

        C_LOG(LOG_LEVEL_DEBUG, "Velocity=%f, Time=%f\n", velocity, time);

        // Check termination conditions
        if (velocity < _cMinimumVelocity)
        {
            *reason = RANGE_ERROR_MINIMUM_VELOCITY_REACHED;
        }
        else if (range_vector.y < _cMaximumDrop)
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

    C_LOG(LOG_LEVEL_DEBUG, "Loop exited, appending final point\n");

    // Process final data point

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

    // PUSH_ERR(&eng->err_stack, ZERO_DIVISION_ERROR, SRC_INTEGRATE, "fake error");
    // return STATUS_ERROR;

    return STATUS_SUCCESS;
}
