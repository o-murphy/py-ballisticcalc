#include "engine.h"

// int Engine_t_init_trajectory(Engine_t *engine) {
//     if (engine == NULL) {
//         return -1;
//     }

// }

void Engine_t_release_trajectory(Engine_t *engine)
{
    if (engine == NULL)
    {
        return;
    }
    ShotProps_t_release(&engine->shot);
}

TerminationReason Engine_t_integrate(
    IntegrateFuncPtr integrate_func,
    Engine_t *engine,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr)
{
    if (!engine)
    {
        return RangeErrorInvalidParameter;
    }
    if (!traj_seq_ptr)
    {
        return RangeErrorInvalidParameter;
    }
    return integrate_func(&engine->shot, &engine->config, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);
}
