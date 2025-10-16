#include <math.h>
#include "rk4.h"
// #include <stdio.h>  // for printf (DEBUG)

/**
 * @brief Calculate the derivative of velocity with respect to time (acceleration).
 * * Assumes all necessary types (V3dT, ShotProps_t, Coriolis_t) and vector
 * functions (mulS, mag, sub, add, Coriolis_t_coriolis_acceleration_local)
 * are declared and defined in relevant C headers.
 * * @param v_ptr Pointer to the relative velocity vector (velocity - wind).
 * @param gravity_vector_ptr Pointer to the gravity vector.
 * @param km_coeff Drag coefficient.
 * @param shot_props_ptr Pointer to shot properties (for Coriolis data).
 * @param ground_velocity_ptr Pointer to ground velocity vector (for Coriolis calculation).
 * @return V3dT The acceleration vector (dv/dt).
 */
V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff,
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
 * @return TerminationReason An enumeration value indicating why the integration
 * loop was terminated (e.g., NoRangeError on successful completion).
 */
TerminationReason _integrate_rk4(const ShotProps_t *shot_props_ptr,
                                 WindSock_t *wind_sock_ptr,
                                 const Config_t *config_ptr,
                                 double range_limit_ft, double range_step_ft,
                                 double time_step, int filter_flags,
                                 BaseTrajSeq_t *traj_seq_ptr)
{
    // printf("DEBUG: Function entry\n");
    // fflush(stdout);

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

    // printf("DEBUG: All pointers valid\n");
    // fflush(stdout);

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

    // printf("DEBUG: Variables declared\n");
    // fflush(stdout);

    // Early binding of configuration constants
    double _cMinimumVelocity = config_ptr->cMinimumVelocity;
    double _cMinimumAltitude = config_ptr->cMinimumAltitude;
    double _cMaximumDrop = -fabs(config_ptr->cMaximumDrop);

    // printf("DEBUG: Config values read: minVel=%f, minAlt=%f, maxDrop=%f\n",
    //        _cMinimumVelocity, _cMinimumAltitude, _cMaximumDrop);
    // fflush(stdout);

    // Working variables
    TerminationReason termination_reason = NoRangeError;
    double relative_speed;
    V3dT _dir_vector;
    int integration_step_count = 0;

    // RK4 specific variables
    V3dT _temp_add_operand;
    V3dT _temp_v_result;
    V3dT _v_sum_intermediate;
    V3dT _p_sum_intermediate;
    V3dT v1, v2, v3, v4;
    V3dT p1, p2, p3, p4;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = config_ptr->cGravityConstant;
    gravity_vector.z = 0.0;

    // printf("DEBUG: Gravity initialized: %f\n", gravity_vector.y);
    // fflush(stdout);

    // Initialize wind vector
    // printf("DEBUG: About to call WindSock_t_currentVector\n");
    // fflush(stdout);
    wind_vector = WindSock_t_currentVector(wind_sock_ptr);
    // printf("DEBUG: Wind vector: %f, %f, %f\n", wind_vector.x, wind_vector.y, wind_vector.z);
    // fflush(stdout);

    // Initialize velocity and position vectors
    velocity = shot_props_ptr->muzzle_velocity;
    calc_step = shot_props_ptr->calc_step;

    // printf("DEBUG: velocity=%f, calc_step=%f\n", velocity, calc_step);
    // fflush(stdout);

    // Set range_vector components directly
    range_vector.x = 0.0;
    range_vector.y = -shot_props_ptr->cant_cosine * shot_props_ptr->sight_height;
    range_vector.z = -shot_props_ptr->cant_sine * shot_props_ptr->sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y);

    // printf("DEBUG: range_vector: %f, %f, %f\n", range_vector.x, range_vector.y, range_vector.z);
    // fflush(stdout);

    // Set direction vector components
    _dir_vector.x = cos(shot_props_ptr->barrel_elevation) * cos(shot_props_ptr->barrel_azimuth);
    _dir_vector.y = sin(shot_props_ptr->barrel_elevation);
    _dir_vector.z = cos(shot_props_ptr->barrel_elevation) * sin(shot_props_ptr->barrel_azimuth);

    // printf("DEBUG: dir_vector: %f, %f, %f\n", _dir_vector.x, _dir_vector.y, _dir_vector.z);
    // fflush(stdout);

    // Calculate velocity vector
    // printf("DEBUG: About to call mulS\n");
    // fflush(stdout);
    velocity_vector = mulS(&_dir_vector, velocity);
    // printf("DEBUG: velocity_vector: %f, %f, %f\n", velocity_vector.x, velocity_vector.y, velocity_vector.z);
    // fflush(stdout);

    // printf("DEBUG: About to call Atmosphere_t_updateDensityFactorAndMachForAltitude\n");
    // fflush(stdout);
    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &shot_props_ptr->atmo,
        shot_props_ptr->alt0 + range_vector.y,
        &density_ratio,
        &mach);
    // printf("DEBUG: density_ratio=%f, mach=%f\n", density_ratio, mach);
    // fflush(stdout);

    // Trajectory Loop
    // printf("DEBUG: Entering main loop, range_limit_ft=%f\n", range_limit_ft);
    // fflush(stdout);

    while (range_vector.x <= range_limit_ft || integration_step_count < 3)
    {
        // printf("DEBUG: Loop iteration %d, range_x=%f\n", integration_step_count, range_vector.x);
        // fflush(stdout);

        integration_step_count++;

        // Update wind reading at current point in trajectory
        if (range_vector.x >= wind_sock_ptr->next_range)
        {
            // printf("DEBUG: Updating wind vector\n");
            // fflush(stdout);
            wind_vector = WindSock_t_vectorForRange(wind_sock_ptr, range_vector.x);
        }

        // Update air density and mach at current altitude
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &shot_props_ptr->atmo,
            shot_props_ptr->alt0 + range_vector.y,
            &density_ratio,
            &mach);

        // Store point in trajectory sequence
        // printf("DEBUG: About to append to trajectory sequence\n");
        // fflush(stdout);
        BaseTrajSeq_t_append(
            traj_seq_ptr,
            time,
            range_vector.x, range_vector.y, range_vector.z,
            velocity_vector.x, velocity_vector.y, velocity_vector.z,
            mach);
        // printf("DEBUG: Append successful\n");
        // fflush(stdout);

        // Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = sub(&velocity_vector, &wind_vector);
        relative_speed = mag(&relative_velocity);

        delta_time = calc_step;

        // printf("DEBUG: About to call ShotProps_t_dragByMach, relative_speed=%f, mach=%f\n",
        //        relative_speed, mach);
        // fflush(stdout);

        // Check for division by zero
        if (mach == 0.0)
        {
            // printf("ERROR: mach is zero, cannot divide!\n");
            return RangeErrorInvalidParameter;
        }

        km = density_ratio * ShotProps_t_dragByMach(shot_props_ptr, relative_speed / mach);
        // printf("DEBUG: km=%f\n", km);
        // fflush(stdout);

        // region RK4 integration
        // printf("DEBUG: Starting RK4 integration\n");
        // fflush(stdout);

        // v1 = f(relative_velocity)
        v1 = _calculate_dvdt(&relative_velocity, &gravity_vector, km, shot_props_ptr, &velocity_vector);

        // v2 = f(relative_velocity + 0.5 * delta_time * v1)
        _temp_add_operand = mulS(&v1, 0.5 * delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v2 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, shot_props_ptr, &velocity_vector);

        // v3 = f(relative_velocity + 0.5 * delta_time * v2)
        _temp_add_operand = mulS(&v2, 0.5 * delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v3 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, shot_props_ptr, &velocity_vector);

        // v4 = f(relative_velocity + delta_time * v3)
        _temp_add_operand = mulS(&v3, delta_time);
        _temp_v_result = add(&relative_velocity, &_temp_add_operand);
        v4 = _calculate_dvdt(&_temp_v_result, &gravity_vector, km, shot_props_ptr, &velocity_vector);

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

        // printf("DEBUG: RK4 integration complete\n");
        // fflush(stdout);

        // Update time and velocity magnitude
        velocity = mag(&velocity_vector);
        time += delta_time;

        // printf("DEBUG: velocity=%f, time=%f\n", velocity, time);
        // fflush(stdout);

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

    // printf("DEBUG: Loop exited, appending final point\n");
    // fflush(stdout);

    // Process final data point
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