#ifndef BCLIBC_EULER_H
#define BCLIBC_EULER_H

#include "bclibc_v3d.h"
#include "bclibc_bclib.h"
#include "bclibc_engine.h"
#include "bclibc_base_traj_seq.h"

#ifdef __cplusplus
extern "C"
{
#endif

    BCLIBC_StatusCode BCLIBC_integrateEULER(
        BCLIBC_EngineT *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_EULER_H
