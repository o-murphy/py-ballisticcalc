#include "engine.h"

// int Engine_t_init_trajectory(Engine_t *engine_ptr) {
//     if (engine == NULL) {
//         return -1;
//     }

// }

void Engine_t_release_trajectory(Engine_t *engine_ptr)
{
    if (engine_ptr == NULL)
    {
        return;
    }
    ShotProps_t_release(&engine_ptr->shot);
}

TerminationReason Engine_t_integrate(
    Engine_t *engine_ptr,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr)
{
    if (!engine_ptr)
    {
        return RangeErrorInvalidParameter;
    }
    if (!engine_ptr->integrate_func_ptr)
    {
        return RangeErrorInvalidParameter;
    }
    if (!traj_seq_ptr)
    {
        return RangeErrorInvalidParameter;
    }
    return engine_ptr->integrate_func_ptr(engine_ptr, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);
}
