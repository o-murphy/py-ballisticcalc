#include "engine.h"

ErrorCode Engine_t_log_and_save_error(
    Engine_t *eng,
    ErrorCode code,
    const char *file,
    int line,
    const char *func,
    const char *format,
    ...)
{
    va_list args;
    char log_buffer[MAX_ERR_MSG_LEN];

    // Format the message
    va_start(args, format);
    vsnprintf(log_buffer, MAX_ERR_MSG_LEN, format, args);
    va_end(args);

    // Log with the REAL location (passed from macro)
    if (LOG_LEVEL_ERROR >= global_log_level)
    {
        fprintf(stderr, "[ERROR] %s:%d in %s: %s\n", file, line, func, log_buffer);
    }

    // Save error message to engine
    if (eng != NULL && code != NO_ERROR)
    {
        strncpy(eng->err_msg, log_buffer, MAX_ERR_MSG_LEN - 1);
        eng->err_msg[MAX_ERR_MSG_LEN - 1] = '\0';
    }

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
        return Engine_t_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
    }
    if (!eng->integrate_func_ptr)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
    }
    C_LOG(LOG_LEVEL_DEBUG, "Using integration function pointer %p.", (void *)eng->integrate_func_ptr);

    ErrorCode err = eng->integrate_func_ptr(eng, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr);

    if (err != NO_ERROR)
    {
        Engine_t_ERR(eng, err, "error code: %d", err);
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
        C_LOG(LOG_LEVEL_DEBUG, "Integration completed successfully or with acceptable termination code: (%d).", err);
        err = NO_ERROR;
        break;
    default:
        Engine_t_ERR(eng, err, "Critical integration error code: %d", err);
        break;
        // goto finally;
    }

    if (err == NO_ERROR)
    {
        err = BaseTrajSeq_t_get_at(&result, KEY_VEL_Y, 0.0, -1, out);
        if (err != NO_ERROR)
        {
            err = Engine_t_ERR(eng, RUNTIME_ERROR, "Runtime error (No apex flagged in trajectory data)");
        }
    }

    // finally
    if (has_restore_min_velocity)
    {
        eng->config.cMinimumVelocity = restore_min_velocity;
    }

    // finally:

    BaseTrajSeq_t_release(&result);
    return err;
}
