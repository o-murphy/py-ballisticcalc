#include <math.h>
#include "rk4.h"
// #include <stdio.h>  // for printf (DEBUG)

/**
 * @brief Calculate the derivative of velocity with respect to time (acceleration).
 * * Uses V3dT functions that are assumed to take and return V3dT structures by value.
 *
 * @param v_ptr Relative velocity vector (velocity - wind).
 * @param gravity_vector_ptr Gravity vector.
 * @param km_coeff Drag coefficient.
 * @param shot_props_ptr Pointer to shot properties (for Coriolis data).
 * @param ground_velocity_ptr Ground velocity vector (for Coriolis calculation).
 * @return V3dT The acceleration vector (dv/dt).
 */
V3dT _calculate_dvdt(const V3dT v, const V3dT gravity_vector, double km_coeff,
                     const ShotProps_t *shot_props_ptr, const V3dT ground_velocity)
{
    // Local variable for Coriolis, required because the C function modifies it.
    V3dT coriolis_acceleration;

    // Calculate base acceleration using functional chaining:
    // acceleration = sub(gravity_vector_ptr, mulS(v, km_coeff * mag(v)))
    V3dT acceleration = sub(gravity_vector, mulS(v, km_coeff * mag(v)));

    // 3. Add Coriolis acceleration if available
    if (!shot_props_ptr->coriolis.flat_fire_only)
    {
        // Calculate Coriolis acceleration into the local variable
        // NOTE: Coriolis_t_coriolis_acceleration_local requires a pointer for its output,
        // so we cannot eliminate 'coriolis_acceleration' entirely here.
        Coriolis_t_coriolis_acceleration_local(
            &shot_props_ptr->coriolis, &ground_velocity, &coriolis_acceleration);

        // acceleration = add(acceleration, coriolis_acceleration)
        acceleration = add(acceleration, coriolis_acceleration);
    }

    return acceleration;
}

/**
 * @brief Performs trajectory simulation using the Fourth-order Runge-Kutta (RK4) method.
 *
 * @param shot_props_ptr Pointer to the ShotProps_t structure.
 * @param wind_sock_ptr Pointer to the WindSock_t structure.
 * @param config_ptr Pointer to the global Config_t structure.
 * @param range_limit_ft The maximum horizontal range (in feet) to simulate.
 * @param range_step_ft The distance interval for recording filtered points.
 * @param time_step The base time step (dt) used for the RK4 calculation.
 * @param filter_flags Flags (TrajFlag_t) specifying special points to record.
 * @param traj_seq_ptr Pointer to the BaseTrajSeq_t buffer.
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
    if (!shot_props_ptr || !wind_sock_ptr || !config_ptr || !traj_seq_ptr)
    {
        return RangeErrorInvalidParameter;
    }

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

    // Early binding of configuration constants
    double _cMinimumVelocity = config_ptr->cMinimumVelocity;
    double _cMinimumAltitude = config_ptr->cMinimumAltitude;
    double _cMaximumDrop = -fabs(config_ptr->cMaximumDrop);

    // Working variables
    TerminationReason termination_reason = NoRangeError;
    double relative_speed;
    V3dT _dir_vector;
    int integration_step_count = 0;

    // RK4 specific variables (MUST BE KEPT)
    V3dT v1, v2, v3, v4;
    V3dT p1, p2, p3, p4;

    // Initialize gravity vector
    gravity_vector.x = 0.0;
    gravity_vector.y = config_ptr->cGravityConstant;
    gravity_vector.z = 0.0;

    // Initialize wind vector
    wind_vector = WindSock_t_currentVector(wind_sock_ptr);

    // Initialize position vectors
    velocity = shot_props_ptr->muzzle_velocity;
    calc_step = shot_props_ptr->calc_step;

    range_vector.x = 0.0;
    range_vector.y = -shot_props_ptr->cant_cosine * shot_props_ptr->sight_height;
    range_vector.z = -shot_props_ptr->cant_sine * shot_props_ptr->sight_height;
    _cMaximumDrop += fmin(0.0, range_vector.y);

    // Set direction vector components
    _dir_vector.x = cos(shot_props_ptr->barrel_elevation) * cos(shot_props_ptr->barrel_azimuth);
    _dir_vector.y = sin(shot_props_ptr->barrel_elevation);
    _dir_vector.z = cos(shot_props_ptr->barrel_elevation) * sin(shot_props_ptr->barrel_azimuth);

    // Calculate velocity vector
    velocity_vector = mulS(_dir_vector, velocity);

    Atmosphere_t_updateDensityFactorAndMachForAltitude(
        &shot_props_ptr->atmo,
        shot_props_ptr->alt0 + range_vector.y,
        &density_ratio,
        &mach);

    // Trajectory Loop
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

        // Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = sub(velocity_vector, wind_vector);
        relative_speed = mag(relative_velocity);

        delta_time = calc_step;

        // Check for division by zero (mach is in denominator of km calculation)
        if (mach == 0.0)
        {
            return RangeErrorInvalidParameter;
        }

        km = density_ratio * ShotProps_t_dragByMach(shot_props_ptr, relative_speed / mach);

        // region RK4 integration (Optimized for Chaining)

        // v1 = f(relative_velocity)
        v1 = _calculate_dvdt(relative_velocity, gravity_vector, km, shot_props_ptr, velocity_vector);

        // v2 = f(relative_velocity + 0.5 * delta_time * v1)
        v2 = _calculate_dvdt(
            add(relative_velocity, mulS(v1, 0.5 * delta_time)),
            gravity_vector, km, shot_props_ptr, velocity_vector);

        // v3 = f(relative_velocity + 0.5 * delta_time * v2)
        v3 = _calculate_dvdt(
            add(relative_velocity, mulS(v2, 0.5 * delta_time)),
            gravity_vector, km, shot_props_ptr, velocity_vector);

        // v4 = f(relative_velocity + delta_time * v3)
        v4 = _calculate_dvdt(
            add(relative_velocity, mulS(v3, delta_time)),
            gravity_vector, km, shot_props_ptr, velocity_vector);

        // p1 = velocity_vector
        p1 = velocity_vector;

        // p2 = (velocity_vector + 0.5 * delta_time * v1)
        p2 = add(velocity_vector, mulS(v1, 0.5 * delta_time));

        // p3 = (velocity_vector + 0.5 * delta_time * v2)
        p3 = add(velocity_vector, mulS(v2, 0.5 * delta_time));

        // p4 = (velocity_vector + delta_time * v3)
        p4 = add(velocity_vector, mulS(v3, delta_time));

        // velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)
        // Chain the addition operations
        velocity_vector = add(
            velocity_vector,
            mulS(
                add(add(add(v1, mulS(v2, 2.0)), mulS(v3, 2.0)), v4),
                (delta_time / 6.0)
            )
        );

        // range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)
        // Chain the addition operations
        range_vector = add(
            range_vector,
            mulS(
                add(add(add(p1, mulS(p2, 2.0)), mulS(p3, 2.0)), p4),
                (delta_time / 6.0)
            )
        );

        // endregion RK4 integration

        // Update time and velocity magnitude
        velocity = mag(velocity_vector);
        time += delta_time;

        // Check termination conditions
        if (
            velocity < _cMinimumVelocity || (velocity_vector.y <= 0 && range_vector.y < _cMaximumDrop) || (velocity_vector.y <= 0 && shot_props_ptr->alt0 + range_vector.y < _cMinimumAltitude))
        {
            if (velocity < _cMinimumVelocity)
            {
                termination_reason = RangeErrorMinimumVelocityReached;
            }
            else if (range_vector.y < _cMaximumDrop)
            {
                termination_reason = RangeErrorMaximumDropReached;
            }
            else
            {
                termination_reason = RangeErrorMinimumAltitudeReached;
            }
            break;
        }
    }

    // Process final data point
    BaseTrajSeq_t_append(
        traj_seq_ptr,
        time,
        range_vector.x, range_vector.y, range_vector.z,
        velocity_vector.x, velocity_vector.y, velocity_vector.z,
        mach);

    return termination_reason;
}
