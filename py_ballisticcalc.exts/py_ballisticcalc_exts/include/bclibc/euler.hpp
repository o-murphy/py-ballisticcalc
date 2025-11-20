#ifndef BCLIBC_EULER_HPP
#define BCLIBC_EULER_HPP

#include "v3d.hpp"
#include "base_types.hpp"
#include "engine.hpp"
#include "bclibc/traj_data.hpp"

#ifdef __cplusplus
extern "C"
{
#endif

    namespace bclibc
    {

        BCLIBC_StatusCode BCLIBC_integrateEULER(
            BCLIBC_Engine *eng,
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajDataHandlerInterface *handler,
            BCLIBC_TerminationReason *reason);

    };

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_EULER_HPP
