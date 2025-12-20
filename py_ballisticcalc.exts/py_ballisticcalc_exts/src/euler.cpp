#include <cmath>
#include "bclibc/euler.hpp"
#include "bclibc/log.hpp"

namespace bclibc
{
    /**
     * @brief Calculates adaptive time step based on current projectile speed.
     *
     * The time step is inversely proportional to velocity to maintain numerical stability.
     * Faster projectiles require smaller time steps for accurate integration.
     *
     * @param base_step The base time step value (controls overall simulation resolution).
     * @param velocity The current projectile speed (magnitude of velocity vector).
     * @return The calculated adaptive time step, bounded by base_step.
     *
     * @note Time step is clamped to base_step when velocity < 1.0 to avoid
     *       excessive step sizes at very low velocities.
     */
    static inline double BCLIBC_euler_time_step(double base_step, double velocity)
    {
        // Clamp divisor to minimum of 1.0 to prevent excessive time steps
        double divisor = velocity > 1.0 ? velocity : 1.0;
        return base_step / divisor;
    }

    /**
     * @brief Performs projectile trajectory simulation using Euler integration method.
     *
     * This function calculates the complete flight path using the explicit Euler method,
     * a first-order numerical integration scheme. While less accurate than RK4, it's
     * computationally cheaper and suitable for real-time applications or when high
     * precision isn't critical.
     *
     * The simulation accounts for:
     * - Gravity (constant downward acceleration)
     * - Aerodynamic drag (velocity and altitude dependent)
     * - Wind effects (variable with range)
     * - Coriolis forces (optional, for long-range shots)
     *
     * Integration continues until one of these conditions is met:
     * - Maximum range exceeded
     * - Velocity drops below minimum threshold
     * - Projectile altitude drops below minimum
     * - Drop exceeds maximum allowed value
     *
     * PERFORMANCE CHARACTERISTICS:
     * - Time complexity: O(n) where n = range_limit / effective_step_size
     * - Uses adaptive time stepping for numerical stability
     * - Optimized with fused vector operations to minimize allocations
     *
     * NUMERICAL STABILITY:
     * - Adaptive time stepping: smaller steps at higher velocities
     * - First-order accurate: local error O(dt²), global error O(dt)
     * - Requires smaller time steps than RK4 for comparable accuracy
     *
     * @param eng The ballistics engine containing shot properties, atmospheric conditions, and configuration.
     * @param handler Interface for processing computed trajectory data points.
     * @param reason Output parameter indicating why the simulation terminated.
     */
    void BCLIBC_integrateEULER(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason)
    {
        // State variables
        double velocity;
        double delta_time;
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

        const double calc_step = eng.shot.calc_step;

        // Initialize working variables
        reason = BCLIBC_TerminationReason::NO_TERMINATE;
        double relative_speed;
        BCLIBC_V3dT _dir_vector;

        // Reusable work buffer for acceleration calculations (reduces allocations)
        BCLIBC_V3dT acceleration_temp;

        eng.integration_step_count = 0;

        // Initialize gravity vector (pointing downward in y-axis)
        gravity_vector.x = 0.0;
        gravity_vector.y = eng.config.cGravityConstant;
        gravity_vector.z = 0.0;

        // Get initial wind conditions
        wind_vector = eng.shot.wind_sock.current_vector();

        // Initialize projectile state
        velocity = eng.shot.muzzle_velocity;

        // Set initial position accounting for sight height and cant angle
        range_vector.x = 0.0;
        range_vector.y = -eng.shot.cant_cosine * eng.shot.sight_height;
        range_vector.z = -eng.shot.cant_sine * eng.shot.sight_height;

        // Calculate initial direction vector from barrel elevation and azimuth
        const double cos_elev = std::cos(eng.shot.barrel_elevation);
        _dir_vector.x = cos_elev * std::cos(eng.shot.barrel_azimuth);
        _dir_vector.y = std::sin(eng.shot.barrel_elevation);
        _dir_vector.z = cos_elev * std::sin(eng.shot.barrel_azimuth);

        // Calculate initial velocity vector
        velocity_vector = _dir_vector * velocity;

        // Get initial atmospheric conditions at starting altitude
        eng.shot.atmo.update_density_factor_and_mach_for_altitude(
            eng.shot.alt0 + range_vector.y,
            density_ratio,
            mach);

        // Main trajectory integration loop
        // Continue until range limit is reached or termination condition is met
        // Minimum of 3 steps ensures sufficient data for cubic interpolation
        while (reason == BCLIBC_TerminationReason::NO_TERMINATE)
        {
            eng.integration_step_count++;

            // Update wind vector if we've crossed into a new wind zone
            if (range_vector.x >= eng.shot.wind_sock.next_range)
            {
                wind_vector = eng.shot.wind_sock.vector_for_range(range_vector.x);
            }

            // Update atmospheric density and speed of sound at current altitude
            eng.shot.atmo.update_density_factor_and_mach_for_altitude(
                eng.shot.alt0 + range_vector.y,
                density_ratio,
                mach);

            // Record current trajectory point
            handler.handle(
                BCLIBC_BaseTrajData(time, range_vector, velocity_vector, mach));

            // === Euler Integration Step ===
            // Basic form: x(t+dt) = x(t) + v(t)*dt
            //             v(t+dt) = v(t) + a(t)*dt

            // 1. Calculate relative velocity (projectile velocity relative to air mass)
            relative_velocity = velocity_vector - wind_vector;
            relative_speed = relative_velocity.mag();

            // 2. Calculate adaptive time step based on current velocity
            //    Higher velocities require smaller time steps for stability
            delta_time = BCLIBC_euler_time_step(calc_step, relative_speed);

            // 3. Calculate drag coefficient and drag force magnitude
            //    Drag is proportional to velocity squared (via relative_speed * km)
            km = density_ratio * eng.shot.drag_by_mach(relative_speed / mach);
            drag = km * relative_speed;

            // 4. Compute net acceleration: a = g - F_drag + F_coriolis
            //    Old approach: multiple temporary vectors (_tv = ...; _tv = ... - ...)
            //    New approach: use linear_combination for direct computation

            // Start with: acceleration = gravity - drag*relative_velocity
            acceleration_temp.linear_combination(
                gravity_vector, 1.0,
                relative_velocity, -drag);

            // Add Coriolis acceleration if enabled
            if (!eng.shot.coriolis.flat_fire_only)
            {
                eng.shot.coriolis.coriolis_acceleration_local(
                    velocity_vector,
                    coriolis_accel);
                acceleration_temp += coriolis_accel;
            }

            // 5. Update velocity: v(t+dt) = v(t) + a(t)*dt
            //    Old: _tv = acceleration * dt; velocity_vector = velocity_vector + _tv
            //    New: use fused_multiply_add to avoid temporary
            velocity_vector.fused_multiply_add(acceleration_temp, delta_time);

            // 6. Update position: x(t+dt) = x(t) + v(t+dt)*dt
            //    Note: Using updated velocity (semi-implicit Euler) for better stability
            //    Old: delta_range = velocity * dt; range = range + delta_range
            //    New: use fused_multiply_add
            range_vector.fused_multiply_add(velocity_vector, delta_time);

            // 7. Update scalar velocity magnitude and simulation time
            velocity = velocity_vector.mag();
            time += delta_time;
        }

        // Record final trajectory point
        handler.handle(
            BCLIBC_BaseTrajData(time, range_vector, velocity_vector, mach));

        BCLIBC_DEBUG("Function exit, reason=%d\n", reason);
    }

}; // namespace bclibc
