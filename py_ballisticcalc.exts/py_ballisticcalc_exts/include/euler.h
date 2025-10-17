#ifndef EULER_H
#define EULER_H

#include "v3d.h"
#include "bclib.h"
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

    TerminationReason _integrate_euler(const ShotProps_t *shot_props_ptr,
                                       WindSock_t *wind_sock_ptr,
                                       const Config_t *config_ptr,
                                       double range_limit_ft, double range_step_ft,
                                       double time_step, int filter_flags,
                                       BaseTrajSeq_t *traj_seq_ptr);

#ifdef __cplusplus
}
#endif

#endif // EULER_H