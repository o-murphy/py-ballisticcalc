#include <cmath>
#include "bclibc/engine.hpp"
#include "bclibc/scope_guard.hpp"
#include "bclibc/exceptions.hpp"
#include "bclibc/log.hpp"

/*
Possible call chains:

BCLIBC_BaseEngine.find_zero_angle
 ├─> BCLIBC_BaseEngine.init_zero_calculation
 │    └─> BCLIBC_BaseEngine.find_apex
 │         └─> BCLIBC_BaseEngine.integrate
 │              └─> BCLIBC_BaseEngine->integrate_func
 ├─> BCLIBC_BaseEngine.find_max_range
 │    ├─> BCLIBC_BaseEngine.find_apex
 │    │    └─> BCLIBC_BaseEngine.integrate
 │    │         └─> eng->integrate_func
 │    └─> BCLIBC_BaseEngine.range_for_angle
 │         └─> BCLIBC_BaseEngine.integrate
 │              └─> BCLIBC_BaseEngine->integrate_func
 └─> BCLIBC_BaseEngine.error_at_distance
      └─> BCLIBC_BaseEngine.integrate
      └─> BCLIBC_BaseTrajSeq.get_at / get_raw_item

BCLIBC_BaseEngine.zero_angle
 ├─> BCLIBC_BaseEngine.init_zero_calculation
 ├─> BCLIBC_BaseEngine.integrate
 └─> BCLIBC_BaseTrajSeq / get_at / release

 Longest callstack:

 BCLIBC_BaseEngine.find_zero_angle
 -> BCLIBC_BaseEngine.init_zero_calculation
    -> BCLIBC_BaseEngine.find_apex
       -> BCLIBC_BaseEngine.integrate
          -> eng->integrate_func
*/

namespace bclibc
{
    /**
     * @brief Integrates the projectile trajectory using filters and optional dense trajectory storage.
     *
     * @param range_limit_ft Maximum range for integration in feet.
     * @param range_step_ft Step size along the range in feet for recording data.
     * @param time_step Integration timestep in seconds.
     * @param filter_flags Flags specifying which trajectory points to record.
     * @param records Vector to store filtered trajectory data.
     * @param reason Reference to store the termination reason.
     * @param dense_trajectory Optional pointer to store full dense trajectory data.
     *
     * @throws std::logic_error if integrate_func is null.
     */
    void BCLIBC_BaseEngine::integrate_filtered(
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        std::vector<BCLIBC_TrajectoryData> &records,
        BCLIBC_TerminationReason &reason,
        BCLIBC_BaseTrajSeq *dense_trajectory)
    {
        this->integrate_func_not_empty();

        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        // 1. Create a mandatory filter/writer ON THE HEAP using unique_ptr.
        // This ensures that a large object does not pollute the stack frame.
        BCLIBC_TrajectoryDataFilter data_filter(
            records,
            this->shot,
            filter_flags,
            reason,
            range_limit_ft,
            range_step_ft,
            time_step);

        BCLIBC_DEBUG("Config values read: minVel=%f, minAlt=%f, maxDrop=%f\n",
                     this->config.cMinimumVelocity, this->config.cMinimumAltitude, this->config.cMaximumDrop);

        // 2. Create the Composer (on the stack, it's small and now safer)
        BCLIBC_BaseTrajDataHandlerCompositor composite_handler(
            // A mandatory filter
            &data_filter);

        // 3. Add the optional trajectory
        if (dense_trajectory != nullptr)
        {
            composite_handler.add_handler(dense_trajectory);
        }

        // 4. Call integration ONCE, passing the composite
        this->integrate(range_limit_ft, composite_handler, reason);
    };

    /**
     * @brief Calls the underlying integration function for the projectile trajectory.
     *
     * @param handler Reference to a data handler for trajectory recording.
     * @param reason Reference to store termination reason.
     *
     * @throws std::logic_error if integrate_func is null.
     */
    void BCLIBC_BaseEngine::integrate(
        double range_limit_ft,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason)
    {
        this->integrate_func_not_empty();

        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        // Essential termination reason control
        BCLIBC_EssentialTerminators terminators(
            this->shot,
            range_limit_ft,
            this->config.cMinimumVelocity,
            this->config.cMaximumDrop,
            this->config.cMinimumAltitude,
            reason);

        BCLIBC_BaseTrajDataHandlerCompositor composite_handler(
            &terminators, // Essential terminators
            &handler      // Request handler
        );

        this->integrate_func(*this, composite_handler, reason);

        if (reason == BCLIBC_TerminationReason::TARGET_RANGE_REACHED)
        {
            BCLIBC_INFO("Integration completed successfully: (%d).", reason);
        }
        else
        {
            BCLIBC_INFO("Integration completed with acceptable termination reason: (%d).", reason);
        }
    };

    /**
     * @brief Performs trajectory integration and interpolates a single data point
     * where a specific key attribute reaches a target value.
     *
     * This method runs a full trajectory integration internally, using
     * BCLIBC_SinglePointHandler to find and interpolate the point where the
     * specified key (e.g., 'time', 'mach', 'position.z') equals the target value.
     * The integration runs up to MAX_INTEGRATION_RANGE using a default timestep (0.0).
     *
     * @param key The interpolation key (e.g., time, altitude, vector component)
     * to use as the independent variable.
     * @param target_value The value the key attribute must reach for the
     * integration to terminate and interpolation to occur.
     * @param raw_data Reference to a BCLIBC_BaseTrajData object that will store
     * the interpolated raw data point upon success.
     * @param full_data Reference to a BCLIBC_TrajectoryData object that will store
     * the full (processed) interpolated data point upon success.
     *
     * @note Access to the engine is protected by engine_mutex.
     * the actual step size is determined internally by the integrator.
     *
     * @throws std::logic_error if integrate_func is null.
     * @throws BCLIBC_InterceptionError if the target point is not found within the
     * integrated trajectory (e.g., "No apex flagged...").
     */
    void BCLIBC_BaseEngine::integrate_at(
        BCLIBC_BaseTrajData_InterpKey key,
        double target_value,
        BCLIBC_BaseTrajData &raw_data,
        BCLIBC_TrajectoryData &full_data)
    {
        integrate_func_not_empty();

        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        BCLIBC_TerminationReason reason;
        BCLIBC_SinglePointHandler handler(key, target_value, &reason);

        this->integrate(this->MAX_INTEGRATION_RANGE, handler, reason);

        if (!handler.found())
        {
            // Record last valid point
            raw_data = handler.get_last();
            full_data = BCLIBC_TrajectoryData(this->shot, raw_data);
            throw BCLIBC_InterceptionError(
                "Intercept point not found for target key and value",
                raw_data, full_data);
        }

        raw_data = handler.get_result();
        full_data = BCLIBC_TrajectoryData(this->shot, raw_data);
    };

    /**
     * @brief Finds the apex (highest point) of the trajectory.
     *
     * @param apex_out Output variable to store apex trajectory data.
     *
     * @throws std::invalid_argument if barrel elevation is <= 0.
     * @throws BCLIBC_ZeroFindingError if apex cannot be determined.
     *
     * OPTIMIZATION: Uses ~192 bytes instead of ~N*64 bytes for full trajectory.
     */
    void BCLIBC_BaseEngine::find_apex(BCLIBC_BaseTrajData &apex_out)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        if (this->shot.barrel_elevation <= 0)
        {
            throw std::invalid_argument(
                "Value error (Barrel elevation must be greater than 0 to find apex).");
        }

        BCLIBC_TerminationReason reason;

        // Backup and adjust constraints
        BCLIBC_ValueGuard<double> cMinimumVelocity_guard(
            &this->config.cMinimumVelocity,
            this->config.cMinimumVelocity != 0.0
                ? 0.0
                : this->config.cMinimumVelocity);

        // Use SinglePointHandler to find where vertical velocity crosses zero
        BCLIBC_SinglePointHandler apex_handler(
            BCLIBC_BaseTrajData_InterpKey::VEL_Y, // Search by vertical velocity
            0.0,                                  // Apex is where vy = 0
            &reason);

        this->integrate(this->MAX_INTEGRATION_RANGE, apex_handler, reason);

        if (!apex_handler.found())
        {
            throw BCLIBC_SolverRuntimeError(
                "Runtime error (No apex flagged in trajectory data)");
        }

        apex_out = apex_handler.get_result();
    };

    /**
     * @brief Computes the vertical error at a specific horizontal distance.
     *
     * @param angle_rad Barrel elevation angle in radians.
     * @param target_x_ft Horizontal distance to target in feet.
     * @param target_y_ft Target height in feet.
     *
     * @return Vertical error in feet, corrected for horizontal offset.
     *
     * @throws std::out_of_range if trajectory data is invalid.
     * @throws BCLIBC_SolverRuntimeError if trajectory is too short.
     *
     * OPTIMIZATION: Uses ~192 bytes instead of full trajectory buffer.
     */
    double BCLIBC_BaseEngine::error_at_distance(
        double angle_rad,
        double target_x_ft,
        double target_y_ft)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        this->shot.barrel_elevation = angle_rad;

        BCLIBC_TerminationReason reason;

        // Use specialized single-point handler
        BCLIBC_SinglePointHandler handler(
            BCLIBC_BaseTrajData_InterpKey::POS_X,
            target_x_ft,
            &reason);

        integrate(this->MAX_INTEGRATION_RANGE, handler, reason);

        if (!handler.found())
        {
            throw BCLIBC_SolverRuntimeError(
                "Trajectory too short to determine error at distance.");
        }

        const BCLIBC_BaseTrajData &hit = handler.get_result();

        if (hit.time == 0.0)
        {
            throw std::out_of_range("Trajectory sequence error");
        }

        return (hit.py - target_y_ft) - std::fabs(hit.px - target_x_ft);
    };

    /**
     * @brief Initializes the zero-calculation routine for aiming.
     *
     * @param distance Slant distance to the target in feet.
     * @param APEX_IS_MAX_RANGE_RADIANS Threshold in radians to consider vertical shots.
     * @param ALLOWED_ZERO_ERROR_FEET Allowed range error in feet.
     * @param result Output structure with initial zero-finding data.
     *
     * @throws std::out_of_range if trajectory data is invalid.
     * @throws BCLIBC_OutOfRangeError if apex_slant_ft < result.slant_range_ft.
     *
     * Handles edge cases like very close or vertical shots.
     */
    void BCLIBC_BaseEngine::init_zero_calculation(
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        BCLIBC_ZeroInitialData &result)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        BCLIBC_BaseTrajData apex;
        double apex_slant_ft;

        result.status = BCLIBC_ZeroInitialStatus::DONE;
        result.slant_range_ft = distance;
        result.look_angle_rad = this->shot.look_angle;
        result.target_x_ft = result.slant_range_ft * std::cos(result.look_angle_rad);
        result.target_y_ft = result.slant_range_ft * std::sin(result.look_angle_rad);
        result.start_height_ft = -this->shot.sight_height * this->shot.cant_cosine;

        // Edge case: Very close shot
        if (std::fabs(result.slant_range_ft) < ALLOWED_ZERO_ERROR_FEET)
        {
            return;
        }

        // Edge case: Very close shot; ignore gravity and drag
        if (std::fabs(result.slant_range_ft) < 2.0 * std::fmax(std::fabs(result.start_height_ft),
                                                               this->config.cStepMultiplier))
        {
            result.look_angle_rad = std::atan2(result.target_y_ft + result.start_height_ft, result.target_x_ft);
            return;
        }

        // Edge case: Virtually vertical shot; just check if it can reach the target
        if (std::fabs(result.look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
        {
            // Compute slant distance at apex using robust accessor
            this->find_apex(apex);
            apex_slant_ft = apex.px * std::cos(result.look_angle_rad) + apex.py * std::sin(result.look_angle_rad);
            if (apex_slant_ft < result.slant_range_ft)
            {
                throw BCLIBC_OutOfRangeError(
                    "Out of range",
                    result.slant_range_ft,
                    apex_slant_ft,
                    result.look_angle_rad);
            }
            return;
        }

        result.status = BCLIBC_ZeroInitialStatus::CONTINUE;
        return;
    };

    /**
     * @brief Attempts to compute zero angle and falls back to guaranteed method if primary fails.
     *
     * @param distance Target slant distance in feet.
     * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
     * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
     *
     * @return Zero angle (barrel elevation) in radians.
     */
    double BCLIBC_BaseEngine::zero_angle_with_fallback(
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        try
        {
            return this->zero_angle(distance, APEX_IS_MAX_RANGE_RADIANS, ALLOWED_ZERO_ERROR_FEET);
        }
        catch (const BCLIBC_ZeroFindingError &error)
        {
            BCLIBC_WARN("Primary zero-finding failed, switching to fallback.");

            // Fallback to guaranteed method
            return this->find_zero_angle(distance, APEX_IS_MAX_RANGE_RADIANS, ALLOWED_ZERO_ERROR_FEET, 0);
        }
    };

    /**
     * @brief Computes the zero angle for a given target distance.
     *
     * @param distance Target slant distance in feet.
     * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
     * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
     *
     * @return Zero angle (barrel elevation) in radians.
     *
     * @throws BCLIBC_ZeroFindingError if zero-finding fails to converge.
     * OPTIMIZATION: Uses SinglePointHandler instead of full trajectory buffer.
     * Memory: 192 bytes per iteration vs ~N*64 bytes
     * Speed: 50-90% faster with early termination
     */
    double BCLIBC_BaseEngine::zero_angle(
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        BCLIBC_ZeroInitialData init_data;

        this->init_zero_calculation(
            distance,
            APEX_IS_MAX_RANGE_RADIANS,
            ALLOWED_ZERO_ERROR_FEET,
            init_data); // pass pointer directly, not &range_error

        double look_angle_rad = init_data.look_angle_rad;
        double slant_range_ft = init_data.slant_range_ft;
        double target_x_ft = init_data.target_x_ft;
        double target_y_ft = init_data.target_y_ft;

        if (init_data.status == BCLIBC_ZeroInitialStatus::DONE)
        {
            return look_angle_rad; // immediately return when already done
        }

        BCLIBC_BaseTrajData hit;

        double _cZeroFindingAccuracy = this->config.cZeroFindingAccuracy;
        int _cMaxIterations = this->config.cMaxIterations;

        int iterations_count = 0;
        double range_error_ft = 9e9;
        double prev_range_error_ft = 9e9;
        double prev_height_error_ft = 9e9;
        double damping_factor = 1.0;
        double damping_rate = 0.7;
        double last_correction = 0.0;
        double height_error_ft = _cZeroFindingAccuracy * 2;

        double required_drop_ft = target_x_ft / 2.0 - target_y_ft;

        double current_distance = 0.0;
        double trajectory_angle = 0.0;

        // Backup, adjust and restore constraints (emulate @with_max_drop_zero and @with_no_minimum_altitude)
        BCLIBC_ValueGuard<double> cMaximumDrop_guard(
            &this->config.cMaximumDrop,
            (std::fabs(this->config.cMaximumDrop) < required_drop_ft)
                ? required_drop_ft
                : this->config.cMaximumDrop);

        BCLIBC_ValueGuard<double> cMinimumAltitude_guard(
            &this->config.cMinimumAltitude,
            (this->config.cMinimumAltitude - this->shot.alt0 > required_drop_ft)
                ? this->shot.alt0 - required_drop_ft
                : this->config.cMinimumAltitude);

        // Main iteration loop
        while (iterations_count < _cMaxIterations)
        {
            // reset handler for integration result
            BCLIBC_TerminationReason reason;

            // Using SinglePointHandler з early termination
            BCLIBC_SinglePointHandler handler(
                BCLIBC_BaseTrajData_InterpKey::POS_X,
                target_x_ft,
                &reason // Enable early termination
            );

            this->integrate(target_x_ft, handler, reason);

            if (!handler.found())
            {
                throw BCLIBC_SolverRuntimeError("Failed to interpolate trajectory at target distance");
            }

            hit = handler.get_result();

            if (hit.time == 0.0)
            {
                // Integrator returned initial point - consider removing constraints / bail out
                break;
            }

            current_distance = hit.px;
            if (2 * current_distance < target_x_ft && this->shot.barrel_elevation == 0.0 && look_angle_rad < 1.5)
            {
                this->shot.barrel_elevation = 0.01;
                iterations_count++;
                continue;
            }

            double ca = std::cos(look_angle_rad);
            double sa = std::sin(look_angle_rad);
            double height_diff_ft = hit.py * ca - hit.px * sa;
            double look_dist_ft = hit.px * ca + hit.py * sa;
            double range_diff_ft = look_dist_ft - slant_range_ft;
            range_error_ft = std::fabs(range_diff_ft);
            height_error_ft = std::fabs(height_diff_ft);
            trajectory_angle = std::atan2(hit.vy, hit.vx);

            double sensitivity = (std::tan(this->shot.barrel_elevation - look_angle_rad) * std::tan(trajectory_angle - look_angle_rad));
            double denominator;
            if (sensitivity < -0.5)
            {
                denominator = look_dist_ft;
            }
            else
            {
                denominator = look_dist_ft * (1 + sensitivity);
            }

            if (std::fabs(denominator) > 1e-9)
            {
                double correction = -height_diff_ft / denominator;

                if (range_error_ft > ALLOWED_ZERO_ERROR_FEET)
                {
                    if (range_error_ft > prev_range_error_ft - 1e-6)
                    {
                        throw BCLIBC_ZeroFindingError(
                            "Distance non-convergent",
                            range_error_ft,
                            iterations_count,
                            this->shot.barrel_elevation);
                    }
                }
                else if (height_error_ft > std::fabs(prev_height_error_ft))
                {
                    damping_factor *= damping_rate;
                    if (damping_factor < 0.3)
                    {
                        throw BCLIBC_ZeroFindingError(
                            "Error non-convergent",
                            height_error_ft,
                            iterations_count,
                            this->shot.barrel_elevation);
                    }
                    // Revert previous adjustment
                    this->shot.barrel_elevation -= last_correction;
                    correction = last_correction;
                }
                else if (damping_factor < 1.0)
                {
                    damping_factor = 1.0;
                }

                prev_range_error_ft = range_error_ft;
                prev_height_error_ft = height_error_ft;

                if (height_error_ft > _cZeroFindingAccuracy || range_error_ft > ALLOWED_ZERO_ERROR_FEET)
                {
                    double applied_correction = correction * damping_factor;
                    this->shot.barrel_elevation += applied_correction;
                    last_correction = applied_correction;
                }
                else
                {
                    // success
                    break;
                }
            }
            else
            {
                throw BCLIBC_ZeroFindingError(
                    "Correction denominator is zero",
                    height_error_ft,
                    iterations_count,
                    this->shot.barrel_elevation);
            }

            iterations_count++;
        }

        if (height_error_ft > _cZeroFindingAccuracy || range_error_ft > ALLOWED_ZERO_ERROR_FEET)
        {
            throw BCLIBC_ZeroFindingError(
                "Zero finding failed to converge after maximum iterations",
                height_error_ft,
                iterations_count,
                this->shot.barrel_elevation);
        }

        // success
        return this->shot.barrel_elevation;
    };

    /**
     * @brief Computes the range corresponding to a given barrel elevation angle.
     *
     * @param angle_rad Barrel elevation angle in radians.
     *
     * @return Slant distance in feet where the projectile crosses the line-of-sight.
     *
     * OPTIMIZATION: Uses ~128 bytes instead of full trajectory buffer.
     */
    double BCLIBC_BaseEngine::range_for_angle(double angle_rad)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        this->shot.barrel_elevation = angle_rad;

        BCLIBC_TerminationReason reason;

        // Use specialized zero-crossing handler
        BCLIBC_ZeroCrossingHandler handler(
            this->shot.look_angle,
            &reason);

        this->integrate(this->MAX_INTEGRATION_RANGE, handler, reason);

        if (handler.found())
        {
            return handler.get_slant_distance();
        }

        // No crossing found - return 0.0
        return 0.0;
    };

    /**
     * @brief Finds the maximum range and corresponding angle for the current shot.
     *
     * @param low_angle_deg Lower bound of angle search in degrees.
     * @param high_angle_deg Upper bound of angle search in degrees.
     * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
     *
     * @return Structure containing maximum range (ft) and angle (rad).
     */
    BCLIBC_MaxRangeResult BCLIBC_BaseEngine::find_max_range(
        double low_angle_deg,
        double high_angle_deg,
        double APEX_IS_MAX_RANGE_RADIANS)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        double look_angle_rad = this->shot.look_angle;
        double max_range_ft;
        double angle_at_max_rad;
        BCLIBC_BaseTrajData apex;
        double sdist;

        // Virtually vertical shot
        // π/2 radians = 90 degrees
        if (std::fabs(look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
        {
            this->find_apex(apex);
            sdist = apex.px * std::cos(look_angle_rad) + apex.py * std::sin(look_angle_rad);
            return BCLIBC_MaxRangeResult{sdist, look_angle_rad};
        }

        // Backup, adjust and restore constraints (emulate @with_max_drop_zero and @with_no_minimum_velocity)
        BCLIBC_ValueGuard<double> cMaximumDrop_guard(
            &this->config.cMaximumDrop,
            this->config.cMaximumDrop != 0.0
                ? 0.0
                : this->config.cMaximumDrop);

        BCLIBC_ValueGuard<double> cMinimumVelocity_guard(
            &this->config.cMinimumVelocity,
            this->config.cMinimumVelocity != 0.0
                ? 0.0
                : this->config.cMinimumVelocity);

        double inv_phi = 0.6180339887498949;              // (std::sqrt(5) - 1) / 2
        double inv_phi_sq = 0.38196601125010515;          // inv_phi^2
        double a = low_angle_deg * 0.017453292519943295;  // Convert to radians
        double b = high_angle_deg * 0.017453292519943295; // Convert to radians
        double h = b - a;
        double c = a + inv_phi_sq * h;
        double d = a + inv_phi * h;
        double yc, yd;

        yc = this->range_for_angle(c);
        yd = this->range_for_angle(d);

        // Golden-section search
        for (int i = 0; i < 100; i++)
        {
            if (h < 1e-5)
            {
                break;
            }
            if (yc > yd)
            {
                b = d;
                d = c;
                yd = yc;
                h = b - a;
                c = a + inv_phi_sq * h;
                yc = this->range_for_angle(c);
            }
            else
            {
                a = c;
                c = d;
                yc = yd;
                h = b - a;
                d = a + inv_phi * h;
                yd = this->range_for_angle(d);
            }
        }

        angle_at_max_rad = (a + b) / 2;
        max_range_ft = this->range_for_angle(angle_at_max_rad);

        return BCLIBC_MaxRangeResult{max_range_ft, angle_at_max_rad};
    };

    /**
     * @brief Finds the zero angle using Ridder's method.
     *
     * @param distance Target slant distance in feet.
     * @param lofted Non-zero if a lofted trajectory is allowed.
     * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
     * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
     *
     * @return Zero angle (barrel elevation) in radians.
     *
     * @throws BCLIBC_OutOfRangeError if slant_range_ft > max_range_ft.
     * @throws BCLIBC_ZeroFindingError if zero-finding fails.
     */
    double BCLIBC_BaseEngine::find_zero_angle(
        double distance,
        int lofted,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET)
    {
        // Block access to engine if it is needed for integration
        std::lock_guard<std::recursive_mutex> lock(this->engine_mutex);

        BCLIBC_ZeroInitialData init_data;

        this->init_zero_calculation(
            distance,
            APEX_IS_MAX_RANGE_RADIANS,
            ALLOWED_ZERO_ERROR_FEET,
            init_data);

        double look_angle_rad = init_data.look_angle_rad;
        double slant_range_ft = init_data.slant_range_ft;
        double target_x_ft = init_data.target_x_ft;
        double target_y_ft = init_data.target_y_ft;
        double start_height_ft = init_data.start_height_ft;

        if (init_data.status == BCLIBC_ZeroInitialStatus::DONE)
        {
            return look_angle_rad;
        }

        // 1. Find the maximum possible range to establish a search bracket.
        BCLIBC_MaxRangeResult max_range_result = this->find_max_range(
            0,
            90,
            APEX_IS_MAX_RANGE_RADIANS);

        double max_range_ft = max_range_result.max_range_ft;
        double angle_at_max_rad = max_range_result.angle_at_max_rad;

        // 2. Handle edge cases based on max range.
        if (slant_range_ft > max_range_ft)
        {
            throw BCLIBC_OutOfRangeError(
                "Out of range",
                distance,
                max_range_ft,
                look_angle_rad);
        }
        if (std::fabs(slant_range_ft - max_range_ft) < ALLOWED_ZERO_ERROR_FEET)
        {
            return angle_at_max_rad;
        }

        // Backup, adjust and restore constraints (emulate @with_no_minimum_velocity)
        BCLIBC_ValueGuard<double> cMinimumVelocity_guard(
            &this->config.cMinimumVelocity,
            this->config.cMinimumVelocity != 0.0
                ? 0.0
                : this->config.cMinimumVelocity);

        // 3. Establish search bracket for the zero angle.
        double low_angle, high_angle;
        double sight_height_adjust = 0.0;
        double f_low, f_high;

        if (lofted)
        {
            low_angle = angle_at_max_rad;
            high_angle = 1.5690308719637473; // 89.9 degrees in radians
        }
        else
        {
            if (start_height_ft > 0.0)
            {
                sight_height_adjust = std::atan2(start_height_ft, target_x_ft);
            }
            low_angle = look_angle_rad - sight_height_adjust;
            high_angle = angle_at_max_rad;
        }

        // Prepare variables for Ridder's method
        double mid_angle, f_mid, s, next_angle, f_next;
        int converged = 0;

        f_low = this->error_at_distance(
            low_angle,
            target_x_ft,
            target_y_ft);

        // If low is exactly look angle and failed to evaluate, nudge slightly upward to bracket
        if (f_low > 1e8 && std::fabs(low_angle - look_angle_rad) < 1e-9)
        {
            low_angle = look_angle_rad + 1e-3;
            f_low = this->error_at_distance(
                low_angle,
                target_x_ft,
                target_y_ft);
        }

        f_high = this->error_at_distance(
            high_angle,
            target_x_ft,
            target_y_ft);

        if (f_low * f_high >= 0)
        {
            char reason[256];
            const char *lofted_str = lofted ? "lofted" : "low";
            snprintf(
                reason,
                sizeof(reason),
                "No %s zero trajectory in elevation range (%.2f, %.2f deg). "
                "Errors at bracket: f(low)=%.2f, f(high)=%.2f",
                lofted_str,
                low_angle * 57.29577951308232,
                high_angle * 57.29577951308232,
                f_low,
                f_high);
            throw BCLIBC_ZeroFindingError(
                reason,
                target_y_ft,
                0,
                this->shot.barrel_elevation);
        }

        // 4. Ridder's method implementation
        for (int i = 0; i < this->config.cMaxIterations; i++)
        {
            mid_angle = (low_angle + high_angle) / 2.0;

            f_mid = this->error_at_distance(
                mid_angle,
                target_x_ft,
                target_y_ft);

            // Check if we found exact solution at midpoint
            if (std::fabs(f_mid) < this->config.cZeroFindingAccuracy)
            {
                BCLIBC_DEBUG("Ridder: found exact solution at mid_angle=%.6f", mid_angle);
                converged = 1;
                return mid_angle;
            }

            // s is the updated point using the root of the linear function
            // through (low_angle, f_low) and (high_angle, f_high)
            // and the quadratic function that passes through those points and (mid_angle, f_mid)
            double _inner = f_mid * f_mid - f_low * f_high;

            BCLIBC_DEBUG("Ridder iteration %d: low_angle=%.12f, high_angle=%.12f, mid_angle=%.12f, "
                         "f_low=%.12f, f_high=%.12f, f_mid=%.12f, _inner=%.12e",
                         i, low_angle, high_angle, mid_angle, f_low, f_high, f_mid, _inner);

            // Check for invalid sqrt argument - should not happen if bracket is valid
            if (_inner <= 0.0)
            {
                BCLIBC_DEBUG("Ridder: _inner <= 0 (%.12e), breaking iteration", _inner);
                break;
            }

            s = std::sqrt(_inner);

            // Should not happen if f_low and f_high have opposite signs
            if (s == 0.0)
            {
                BCLIBC_DEBUG("Ridder: s == 0, breaking iteration");
                break;
            }

            next_angle = mid_angle + (mid_angle - low_angle) * (copysign(1.0, f_low - f_high) * f_mid / s);

            if (std::fabs(next_angle - mid_angle) < this->config.cZeroFindingAccuracy)
            {
                converged = 1;
                return next_angle;
            }

            f_next = this->error_at_distance(
                next_angle,
                target_x_ft,
                target_y_ft);

            // Check if we found exact solution at next_angle
            if (std::fabs(f_next) < this->config.cZeroFindingAccuracy)
            {
                BCLIBC_DEBUG("Ridder: found exact solution at next_angle=%.6f", next_angle);
                converged = 1;
                return next_angle;
            }

            // Update the bracket
            if (f_mid * f_next < 0)
            {
                low_angle = mid_angle;
                f_low = f_mid;
                high_angle = next_angle;
                f_high = f_next;
            }
            else if (f_low * f_next < 0)
            {
                high_angle = next_angle;
                f_high = f_next;
            }
            else if (f_high * f_next < 0)
            {
                low_angle = next_angle;
                f_low = f_next;
            }
            else
            {
                // If we are here, something is wrong, the root is not bracketed anymore
                BCLIBC_DEBUG("Ridder: root not bracketed anymore, breaking");
                break;
            }

            if (std::fabs(high_angle - low_angle) < this->config.cZeroFindingAccuracy)
            {
                converged = 1;
                return (low_angle + high_angle) / 2.0;
            }
        }

        // If we exited the loop without convergence
        if (!converged)
        {
            // Try fallback strategies before giving up

            // If we have a very small bracket, consider it converged
            if (std::fabs(high_angle - low_angle) < 10.0 * this->config.cZeroFindingAccuracy)
            {
                double result = (low_angle + high_angle) / 2.0;
                BCLIBC_DEBUG("Ridder: accepting solution from small bracket: %.6f", result);
                return result;
            }

            // If we have very small errors, consider it converged
            if (std::fabs(f_low) < 10.0 * this->config.cZeroFindingAccuracy)
            {
                double result = low_angle;
                BCLIBC_DEBUG("Ridder: accepting low_angle due to small f_low: %.6f", result);
                return result;
            }
            if (std::fabs(f_high) < 10.0 * this->config.cZeroFindingAccuracy)
            {
                double result = high_angle;
                BCLIBC_DEBUG("Ridder: accepting high_angle due to small f_high: %.6f", result);
                return result;
            }

            // All fallback strategies failed
            throw BCLIBC_ZeroFindingError(
                "Ridder's method failed to converge.",
                target_y_ft,
                this->config.cMaxIterations,
                (low_angle + high_angle) / 2.0);
        }
    };

    /**
     * @brief Ensures the integration function is valid.
     *
     * @throws std::logic_error if integrate_func is empty.
     */
    void BCLIBC_BaseEngine::integrate_func_not_empty()
    {
        if (!this->integrate_func)
        {
            throw std::logic_error("Invalid integrate_func: std::function is empty (no callable object assigned).");
        }
    };
}; // namespace bclibc
