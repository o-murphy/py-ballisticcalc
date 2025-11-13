#ifndef BCLIBC_EULER_H
#define BCLIBC_EULER_H

#include "bclibc_v3d.h"
#include "bclibc_bclib.hpp"
#include "bclibc_engine.hpp"
#include "bclibc_seq.hpp"

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
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason);

    };

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_EULER_H
