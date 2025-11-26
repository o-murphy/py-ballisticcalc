#ifndef BCLIBC_RK4_HPP
#define BCLIBC_RK4_HPP

#include "bclibc/v3d.hpp"
#include "bclibc/base_types.hpp"
#include "bclibc/engine.hpp"
#include "bclibc/traj_data.hpp"

#ifdef __cplusplus
extern "C"
{
#endif

    namespace bclibc
    {

        /**
         * @brief Calculates the derivative of velocity with respect to time (acceleration).
         *
         * Computes the acceleration vector considering drag forces, gravity, and optionally
         * Coriolis effects. The drag force is proportional to the velocity magnitude and
         * direction.
         *
         * @param v The relative velocity vector (projectile velocity minus wind velocity).
         * @param gravity_vector The gravity acceleration vector.
         * @param km_coeff The drag coefficient (dimensionless, includes density and ballistic factors).
         * @param shot_props The shot properties containing Coriolis configuration data.
         * @param ground_velocity The absolute ground velocity vector (used for Coriolis calculation).
         * @param acceleration Output parameter for the computed acceleration vector.
         */
        void BCLIBC_integrateRK4(
            BCLIBC_Engine &eng,
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason);

    };

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_RK4_HPP
