#ifndef BCLIBC_RK4_HPP
#define BCLIBC_RK4_HPP

#include "v3d.hpp"
#include "base_types.hpp"
#include "engine.hpp"
#include "traj_seq.hpp"

#ifdef __cplusplus
extern "C"
{
#endif

    namespace bclibc
    {

        BCLIBC_StatusCode BCLIBC_integrateRK4(
            BCLIBC_Engine *eng,
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason);

    };

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_RK4_HPP
