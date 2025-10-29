#ifndef BCLIB_RK4_H
#define BCLIB_RK4_H

#include "v3d.h"
#include "bclib.h"
#include "engine.h"
#include "base_traj_seq.h"

#ifdef __cplusplus
extern "C"
{
#endif

    StatusCode _integrate_rk4(
        Engine_t *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr,
        TerminationReason *reason);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_RK4_H
