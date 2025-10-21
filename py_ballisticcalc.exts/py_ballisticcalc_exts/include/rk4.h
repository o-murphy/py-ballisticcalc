#ifndef RK4_H
#define RK4_H

#include "v3d.h"
#include "bclib.h"
#include "engine.h"
#include "base_traj_seq.h"

#ifdef __cplusplus
extern "C"
{
#endif

    V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff,
                         const ShotProps_t *shot_props_ptr, const V3dT *ground_velocity_ptr);

    TerminationReason _integrate_rk4(Engine_t *engine_ptr,
                                     double range_limit_ft, double range_step_ft,
                                     double time_step, TrajFlag_t filter_flags,
                                     BaseTrajSeq_t *traj_seq_ptr);

#ifdef __cplusplus
}
#endif

#endif // RK4_H