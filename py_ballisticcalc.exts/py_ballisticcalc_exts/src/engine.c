#include "engine.h"

static void Engine_t_vsave_err(Engine_t *eng, const char *format, va_list args)
{
    memset(eng->err_msg, 0, MAX_ERR_MSG_LEN);

    vsnprintf(
        eng->err_msg,
        MAX_ERR_MSG_LEN,
        format,
        args);
}

ErrorCode Engine_t_save_err_internal(Engine_t *eng, const char *format, ...)
{
    va_list args;

    if (!eng)
    {
        return INPUT_ERROR; // Не можемо зберегти помилку
    }

    va_start(args, format);

    Engine_t_vsave_err(eng, format, args);

    va_end(args);

    return NO_ERROR;
}

// This function replaces the logic of the non-portable Engine_t_ERR macro.
ErrorCode Engine_t_handle_error_and_log(
    Engine_t *eng,
    ErrorCode code,
    const char *format,
    ...)
{
    va_list args_log;
    va_list args_save;

    // 1. Logging (Replicating C_LOG(LOG_LEVEL_ERROR, ...) functionality)
    if (LOG_LEVEL_ERROR >= global_log_level)
    {
        va_start(args_log, format);
        char log_buffer[MAX_ERR_MSG_LEN];
        vsnprintf(log_buffer, MAX_ERR_MSG_LEN, format, args_log);
        va_end(args_log);
        fprintf(stderr, "[ERROR] %s\n", log_buffer);
    }

    // 2. Error Saving (Replicating the conditional error save)
    if (eng != NULL && code != NO_ERROR)
    {
        va_start(args_save, format);
        Engine_t_vsave_err(eng, format, args_save);
        va_end(args_save);
    }

    // 3. Return the error code (Replicating the return value of the macro)
    return code;
}

void Engine_t_release_trajectory(Engine_t *eng)
{
    if (eng == NULL)
    {
        return;
    }
    ShotProps_t_release(&eng->shot);
    // NOTE: It is not neccessary to NULLIFY integrate_func_ptr
}

ErrorCode Engine_t_integrate(
    Engine_t *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr)
{
    if (!eng || !traj_seq_ptr)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Engine_t_integrate: Invalid input (NULL pointer).");
    }
    if (!eng->integrate_func_ptr)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Engine_t_integrate: Invalid input (NULL pointer).");
    }
    C_LOG(LOG_LEVEL_DEBUG, "Engine_t_integrate: Using integration function pointer %p.", (void *)eng->integrate_func_ptr);

    ErrorCode err = eng->integrate_func_ptr(eng, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);

    if (err != NO_ERROR)
    {
        Engine_t_ERR(eng, err, "Engine_t_integrate: error code: %d", err);
    }
    return err;
}

ErrorCode Engine_t_find_apex(Engine_t *eng, BaseTrajData_t *out)
{
    if (!eng || !out)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Engine_t_find_apex: Invalid input (NULL pointer).");
    }

    if (eng->shot.barrel_elevation <= 0)
    {
        return Engine_t_ERR(eng, VALUE_ERROR, "Engine_t_find_apex: Value error (Barrel elevation must be greater than 0 to find apex).");
    }

    // Have to ensure cMinimumVelocity is 0 for this to work
    double restore_min_velocity = 0.0;
    int has_restore_min_velocity = 0;
    BaseTrajSeq_t result;
    ErrorCode err;

    BaseTrajSeq_t_init(&result);

    if (eng->config.cMinimumVelocity > 0.0)
    {
        restore_min_velocity = eng->config.cMinimumVelocity;
        eng->config.cMinimumVelocity = 0.0;
        has_restore_min_velocity = 1;
    }

    // try
    err = Engine_t_integrate(eng, 9e9, 9e9, 0.0, TFLAG_APEX, &result);
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
        Engine_t_ERR(eng, err, "Engine_t_find_apex: Critical integration error code: %d", err);
        break;
        // goto interupt;
    }

    if (err == NO_ERROR)
    {
        err = BaseTrajSeq_t_get_at(&result, KEY_VEL_Y, 0.0, -1, out);
        if (err != NO_ERROR)
        {
            err = Engine_t_ERR(eng, RUNTIME_ERROR, "Engine_t_find_apex: Runtime error (No apex flagged in trajectory data)");
        }
    }

    // finally
    if (has_restore_min_velocity)
    {
        eng->config.cMinimumVelocity = restore_min_velocity;
    }

    // interupt:

    BaseTrajSeq_t_release(&result);
    return err;
}
