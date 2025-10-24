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

int isRangeError(ErrorCode err)
{
    return (err & RANGE_ERROR) != 0;
    // switch (err)
    // {
    // case RANGE_ERROR:
    // case RANGE_ERROR_MAXIMUM_DROP_REACHED:
    // case RANGE_ERROR_MINIMUM_ALTITUDE_REACHED:
    // case RANGE_ERROR_MINIMUM_VELOCITY_REACHED:
    //     return 1;
    // default:
    //     return 0;
    // }
}

int isSequenceError(ErrorCode err)
{
    return (err & SEQUENCE_ERROR) != 0;
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

    // redirect last error message
    if (err != NO_ERROR)
    {
        if (isRangeError(err))
        {
            C_LOG(LOG_LEVEL_INFO, "%s: termination reason: %d", eng->err_msg, err);
        }
        else
        {
            Engine_t_ERR(eng, err, "%s: error code: %d", eng->err_msg, err);
        }
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
    if (err == NO_ERROR || isRangeError(err))
    {
        // Do not mask Engine_t_integrate error
        C_LOG(LOG_LEVEL_INFO, "Integration completed successfully or with acceptable termination code: (%d).", err);

        err = NO_ERROR;
        err = BaseTrajSeq_t_get_at(&result, KEY_VEL_Y, 0.0, -1, out);
        if (err != NO_ERROR)
        {
            err = Engine_t_ERR(eng, RUNTIME_ERROR, "Runtime error (No apex flagged in trajectory data)");
        }
    }
    else
    {
        Engine_t_ERR(eng, err, "Critical: integration error: %s, error code: %d", eng->err_msg, err);
        // goto finally;
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

ErrorCode Engine_t_error_at_distance(
    Engine_t *eng,
    double angle_rad,
    double target_x_ft,
    double target_y_ft,
    double *out_error_ft)
{
    *out_error_ft = 9e9;

    if (!eng || !out_error_ft)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
    }

    BaseTrajSeq_t trajectory;
    BaseTrajData_t hit;
    BaseTraj_t *last_ptr;

    BaseTrajSeq_t_init(&trajectory);

    // try

    eng->shot.barrel_elevation = angle_rad;

    ErrorCode err = Engine_t_integrate(
        eng,
        target_x_ft,
        target_x_ft,
        0.0,
        TFLAG_NONE,
        &trajectory);

    if (err == NO_ERROR || isRangeError(err))
    {
        // If trajectory is too short for cubic interpolation, treat as unreachable
        if (trajectory.length >= 3)
        {
            last_ptr = BaseTrajSeq_t_get_raw_item(&trajectory, -1);
            if (last_ptr != NULL && last_ptr->time != 0.0)
            {
                if (BaseTrajSeq_t_get_at(&trajectory, KEY_POS_X, target_x_ft, -1, &hit) == NO_ERROR)
                {
                    // FIXME: possible fix ?
                    // *out_error_ft = (hit.position.y - target_y_ft) - fabs(hit.position.x - target_x_ft);
                    *out_error_ft = hit.position.y - target_y_ft;
                }
            }
        }
    }
    else
    {
        if (err == VALUE_ERROR)
        {
            err = Engine_t_ERR(eng, err, "Value error, %d", err);
        }
        else // < RANGE_ERROR
        {
            err = Engine_t_ERR(eng, err, "Failed to integrate trajectory for error_at_distance, error code: %d", err);
        }
    }

    // finally:
    BaseTrajSeq_t_release(&trajectory);
    return err;
};

ErrorCode Engine_t_init_zero_calculation(
    Engine_t *eng,
    double distance,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    ZeroInitialData_t *result,
    OutOfRangeError_t *error)
{

    if (!eng || !result || !error)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
    }

    ErrorCode err;
    BaseTrajData_t apex;
    double apex_slant_ft;

    result->slant_range_ft = distance;
    result->look_angle_rad = eng->shot.look_angle;
    result->target_x_ft = result->slant_range_ft * cos(result->look_angle_rad);
    result->target_y_ft = result->slant_range_ft * sin(result->look_angle_rad);
    result->start_height_ft = -eng->shot.sight_height * eng->shot.cant_cosine;

    // Edge case: Very close shot
    if (fabs(result->slant_range_ft) < ALLOWED_ZERO_ERROR_FEET)
    {
        return ZERO_INIT_DONE;
    }

    // Edge case: Very close shot; ignore gravity and drag
    if (fabs(result->slant_range_ft) < 2.0 * fmax(fabs(result->start_height_ft),
                                                  eng->config.cStepMultiplier))
    {
        result->look_angle_rad = atan2(result->target_y_ft + result->start_height_ft, result->target_x_ft);
        return ZERO_INIT_DONE;
    }

    // Edge case: Virtually vertical shot; just check if it can reach the target
    if (fabs(result->look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
    {
        // Compute slant distance at apex using robust accessor
        err = Engine_t_find_apex(eng, &apex);
        if (err != NO_ERROR && !isRangeError(err))
        {
            switch (err)
            {
            case VALUE_ERROR:
                return Engine_t_ERR(eng, err, "Barrel elevation must be greater than 0 to find apex.");
            case RUNTIME_ERROR:
                return Engine_t_ERR(eng, err, "No apex flagged in trajectory data");
            default:
                break;
            }
            // // fix
            // redirect Engine_t_find_apex error
            return Engine_t_ERR(eng, err, "Find apex error: %s: error code: %d", eng->err_msg, err);
        }
        apex_slant_ft = apex.position.x * cos(result->look_angle_rad) + apex.position.y * sin(result->look_angle_rad);
        if (apex_slant_ft < result->slant_range_ft)
        {
            error->requested_distance_ft = result->slant_range_ft;
            error->max_range_ft = apex_slant_ft;
            error->look_angle_rad = result->look_angle_rad;
            return Engine_t_ERR(eng, OUT_OF_RANGE_ERROR, "Out of range");
        }
        return ZERO_INIT_DONE;
    }

    return ZERO_INIT_CONTINUE;
}