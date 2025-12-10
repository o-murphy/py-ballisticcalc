#ifndef BCLIBC_RK4_HPP
#define BCLIBC_RK4_HPP

#include "bclibc/v3d.hpp"
#include "bclibc/base_types.hpp"
#include "bclibc/engine.hpp"
#include "bclibc/traj_data.hpp"

namespace bclibc
{
    /**
     * @brief Calculates the derivative of velocity with respect to time (acceleration).
     *
     * Computes the acceleration vector considering drag forces, gravity, and optionally
     * Coriolis effects. The drag force is proportional to the velocity magnitude and
     * direction.
     *
     * @param eng The ballistics engine containing shot properties, atmospheric conditions, and configuration.
     * @param handler Interface for processing computed trajectory data points.
     * @param reason Output parameter indicating why the simulation terminated.
     */
    void BCLIBC_integrateRK4(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason);

}; // namespace bclibc

#endif // BCLIBC_RK4_HPP
