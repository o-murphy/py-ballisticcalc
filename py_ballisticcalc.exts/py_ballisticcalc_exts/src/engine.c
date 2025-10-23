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
    if (err == NO_ERROR || err >= RANGE_ERROR)
    {
        C_LOG(LOG_LEVEL_DEBUG, "Integration completed successfully or with acceptable termination code: (%d).", err);
        err = NO_ERROR;
    }
    else
    {
        Engine_t_ERR(eng, err, "Critical integration error code: %d", err);
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

    ErrorCode err;
    BaseTrajSeq_t trajectory;
    BaseTrajData_t hit;
    BaseTraj_t *last_ptr;
    ssize_t n;

    BaseTrajSeq_t_init(&trajectory);

    // try

    eng->shot.barrel_elevation = angle_rad;

    err = Engine_t_integrate(
        eng,
        target_x_ft,
        target_x_ft,
        0.0,
        TFLAG_NONE,
        &trajectory);

    if (err == NO_ERROR || err >= RANGE_ERROR)
    {
        // If trajectory is too short for cubic interpolation, treat as unreachable
        if (trajectory.length >= 3)
        {
            last_ptr = BaseTrajSeq_t_get_raw_item(&trajectory, -1);
            if (last_ptr != NULL && last_ptr->time != 0.0)
            {
                if (BaseTrajSeq_t_get_at(&trajectory, KEY_POS_X, target_x_ft, -1, &hit) == NO_ERROR)
                {
                    *out_error_ft = (hit.position.y - target_y_ft) - fabs(hit.position.x - target_x_ft);
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

// ErrorCode Engine_t_init_zero_calculation(
//     Engine_t *eng,
//     double distance,
//     double APEX_IS_MAX_RANGE_RADIANS,
//     double ALLOWED_ZERO_ERROR_FEET,
//     ZeroInitialData_t *result)
// {
//     double slant_range_ft = distance;
//     double look_angle_rad = eng->shot.look_angle;
//     double target_x_ft = slant_range_ft * cos(look_angle_rad);
//     double target_y_ft = slant_range_ft * sin(look_angle_rad);
//     double start_height_ft = -eng->shot.sight_height * eng->shot.cant_cosine;
//     BaseTrajData_t apex;
//     double apex_slant_ft;
//     ErrorCode err;

//     // Edge case: Very close shot
//     if (fabs(slant_range_ft) < ALLOWED_ZERO_ERROR_FEET)
//     {
//         result->status = 1;
//         result->look_angle_rad = look_angle_rad;
//         result->slant_range_ft = slant_range_ft;
//         result->target_x_ft = target_x_ft;
//         result->target_y_ft = target_y_ft;
//         result->start_height_ft = start_height_ft;
//         return NO_ERROR;
//     }

//     // Edge case: Very close shot; ignore gravity and drag
//     if (fabs(slant_range_ft) < 2.0 * fmax(fabs(start_height_ft), eng->config.cStepMultiplier))
//     {
//         result->status = 1;
//         result->look_angle_rad = atan2(target_y_ft + start_height_ft, target_x_ft);
//         result->slant_range_ft = slant_range_ft;
//         result->target_x_ft = target_x_ft;
//         result->target_y_ft = target_y_ft;
//         result->start_height_ft = start_height_ft;
//         return NO_ERROR;
//     }

//     // Edge case: Virtually vertical shot; just check if it can reach the target
//     if (fabs(look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
//     { // π/2 radians = 90 degrees
//         // Compute slant distance at apex using robust accessor
//         err = Engine_t_find_apex(eng, &apex);
//         if (err != NO_ERROR)
//         {
//             return err;
//         }
//         apex_slant_ft = apex.position.x * cos(look_angle_rad) + apex.position.y * sin(look_angle_rad);
//         if (apex_slant_ft < slant_range_ft)
//         {
//             // result->status = 1;
//             // result->look_angle_rad = look_angle_rad;
//             // result->distance = distance;
//             // result->apex_slant_ft = apex_slant_ft;
//             // return RUNTIME_ERROR;
//         }
//         result->status = 1;
//         result->look_angle_rad = look_angle_rad;
//         result->slant_range_ft = slant_range_ft;
//         result->target_x_ft = target_x_ft;
//         result->target_y_ft = target_y_ft;
//         result->start_height_ft = start_height_ft;
//         return NO_ERROR;
//     }

//     result->status = 0;
//     result->look_angle_rad = look_angle_rad;
//     result->slant_range_ft = slant_range_ft;
//     result->target_x_ft = target_x_ft;
//     result->target_y_ft = target_y_ft;
//     result->start_height_ft = start_height_ft;
//     return NO_ERROR;
// }