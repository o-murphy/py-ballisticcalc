#include "engine.h"

void Engine_t_release_trajectory(Engine_t *engine_ptr)
{
    if (engine_ptr == NULL)
    {
        return;
    }
    ShotProps_t_release(&engine_ptr->shot);
    // NOTE: It is not neccessary to NULLIFY integrate_func_ptr
}

ErrorCode Engine_t_integrate(
    Engine_t *engine_ptr,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr)
{
    if (!engine_ptr || !traj_seq_ptr)
    {
        C_LOG(LOG_LEVEL_ERROR, "Engine_t_integrate: Invalid input (NULL pointer).");
        return INPUT_ERROR;
    }
    if (!engine_ptr->integrate_func_ptr)
    {
        C_LOG(LOG_LEVEL_ERROR, "Engine_t_integrate: Invalid input (NULL pointer).");
        return INPUT_ERROR;
    }
    C_LOG(LOG_LEVEL_DEBUG, "Engine_t_integrate: Using integration function pointer %p.", (void *)engine_ptr->integrate_func_ptr);
    return engine_ptr->integrate_func_ptr(engine_ptr, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);
}
