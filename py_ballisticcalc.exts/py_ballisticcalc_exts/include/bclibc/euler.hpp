#ifndef BCLIBC_EULER_HPP
#define BCLIBC_EULER_HPP

#include "v3d.hpp"
#include "base_types.hpp"
#include "engine.hpp"
#include "bclibc/traj_data.hpp"

namespace bclibc
{
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
        BCLIBC_TerminationReason &reason);

}; // namespace bclibc

#endif // BCLIBC_EULER_HPP
