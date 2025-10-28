#ifndef BCLIB_EULER_H
#define BCLIB_EULER_H

#include "v3d.h"
#include "bclib.h"
#include "engine.h"
#include "base_traj_seq.h"

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * @brief Calculate time step based on current projectile speed.
     * @param base_step The base time step value.
     * @param velocity The current projectile speed (magnitude of velocity).
     * @return double The calculated time step.
     */
    double _euler_time_step(double base_step, double velocity);

    StatusCode _integrate_euler(
        Engine_t *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr,
        TerminationReason *reason);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_EULER_H
