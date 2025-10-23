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

    ErrorCode err = engine_ptr->integrate_func_ptr(engine_ptr, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);

    if (err != NO_ERROR)
    {
        C_LOG(LOG_LEVEL_ERROR, "Engine_t_integrate: error code: %d", err);
    }
    return err;
}

ErrorCode Engine_t_find_apex(Engine_t *engine_ptr, BaseTrajData_t *out)
{
    if (!engine_ptr || !out)
    {
        C_LOG(LOG_LEVEL_ERROR, "Engine_t_find_apex: Invalid input (NULL pointer).");
        return INPUT_ERROR;
    }

    if (engine_ptr->shot.barrel_elevation <= 0)
    {
        C_LOG(LOG_LEVEL_ERROR, "Engine_t_find_apex: Value error (Barrel elevation must be greater than 0 to find apex).");
        return VALUE_ERROR;
    }

    // Have to ensure cMinimumVelocity is 0 for this to work
    double restore_min_velocity = 0.0;
    int has_restore_min_velocity = 0;
    BaseTrajSeq_t result;
    ErrorCode err;

    BaseTrajSeq_t_init(&result);

    if (engine_ptr->config.cMinimumVelocity > 0.0)
    {
        restore_min_velocity = engine_ptr->config.cMinimumVelocity;
        engine_ptr->config.cMinimumVelocity = 0.0;
        has_restore_min_velocity = 1;
    }

    // try
    err = Engine_t_integrate(engine_ptr, 9e9, 9e9, 0.0, TFLAG_APEX, &result);
    if (err != NO_ERROR)
    {
        // allow RANGE_ERROR
        switch (err)
        {
        case NO_ERROR:
        case RANGE_ERROR_MAXIMUM_DROP_REACHED:
        case RANGE_ERROR_MINIMUM_ALTITUDE_REACHED:
        case RANGE_ERROR_MINIMUM_VELOCITY_REACHED:
            C_LOG(LOG_LEVEL_DEBUG, "Engine_t_find_apex: Integration completed successfully or with acceptable termination reason (%d).", err);
            err = NO_ERROR;
            break;
        default:
            C_LOG(LOG_LEVEL_ERROR, "Engine_t_find_apex: Critical integration error code: %d", err);
            break;
        }
    }
    else
    {
        err = BaseTrajSeq_t_get_at(&result, KEY_VEL_Y, 0.0, -1, out);
        if (err != NO_ERROR)
        {
            C_LOG(LOG_LEVEL_ERROR, "Engine_t_find_apex: Runtime error (No apex flagged in trajectory data)");
            err = RUNTIME_ERROR;
        }
    }
    // finally
    if (has_restore_min_velocity)
    {
        engine_ptr->config.cMinimumVelocity = restore_min_velocity;
    }

    BaseTrajSeq_t_release(&result);
    return err;
}
