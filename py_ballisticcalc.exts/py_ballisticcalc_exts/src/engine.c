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

ErrorCode Engine_t_zero_angle(
    Engine_t *eng,
    double distance,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    double *result,
    OutOfRangeError_t *range_error,
    ZeroFindingError_t *zero_error)
{
    if (!eng || !result || !range_error || !zero_error)
    {
        return Engine_t_ERR(eng, INPUT_ERROR, "Invalid input (NULL pointer).");
    }

    ZeroInitialData_t init_data;
    ErrorCode status = Engine_t_init_zero_calculation(
        eng,
        distance,
        APEX_IS_MAX_RANGE_RADIANS,
        ALLOWED_ZERO_ERROR_FEET,
        &init_data,
        &range_error);

    if (status != ZERO_INIT_CONTINUE && status != ZERO_INIT_DONE)
    {
        // return status up
        return status;
    }

    double look_angle_rad = init_data.look_angle_rad;
    double slant_range_ft = init_data.slant_range_ft;
    double target_x_ft = init_data.target_x_ft;
    double target_y_ft = init_data.target_y_ft;

    if (status == ZERO_INIT_DONE)
    {
        *result = look_angle_rad;
    }

    BaseTrajData_t hit;
    BaseTrajSeq_t seq;
    ErrorCode err;

    double _cZeroFindingAccuracy = eng->config.cZeroFindingAccuracy;
    int _cMaxIterations = eng->config.cMaxIterations;

    // Enhanced zero-finding variables
    int iterations_count = 0;
    double range_error_ft = 9e9; // Absolute value of error from target distance along sight line
    double prev_range_error_ft = 9e9;
    double prev_height_error_ft = 9e9;
    double damping_factor = 1.0; // Start with no damping
    double damping_rate = 0.7;   // Damping rate for correction
    double last_correction = 0.0;
    double height_error_ft = _cZeroFindingAccuracy * 2; // Absolute value of error from sight line

    // Ensure we can see drop at the target distance when launching along slant angle
    double required_drop_ft = target_x_ft / 2.0 - target_y_ft;
    double restore_cMaximumDrop = 0.0;
    double restore_cMinimumAltitude = 0.0;
    int has_restore_cMaximumDrop = 0;
    int has_restore_cMinimumAltitude = 0;

    double current_distance, height_diff_ft, look_dist_ft, range_diff_ft;
    double trajectory_angle, sensitivity, denominator, correction, applied_correction;
    double ca, sa;

    // Backup and adjust constraints if needed, then ensure single restore via try/finally
    // try:

    if (fabs(eng->config.cMaximumDrop) < required_drop_ft)
    {
        restore_cMaximumDrop = eng->config.cMaximumDrop;
        eng->config.cMaximumDrop = required_drop_ft;
        has_restore_cMaximumDrop = 1;
    }

    if ((eng->config.cMinimumAltitude - eng->shot.alt0) > required_drop_ft)
    {
        restore_cMinimumAltitude = eng->config.cMinimumAltitude;
        eng->config.cMinimumAltitude = eng->shot.alt0 - required_drop_ft;
        has_restore_cMinimumAltitude = 1;
    }

    while (iterations_count < _cMaxIterations)
    {
        // Check height of trajectory at the zero distance (using current barrel_elevation)
        BaseTrajSeq_t_init(&seq);
        err = Engine_t_integrate(eng, target_x_ft, target_x_ft, 0.0, TFLAG_NONE, &seq);

        if (err == NO_ERROR || isRangeError(err))
        {
            // Do not mask Engine_t_integrate error
            C_LOG(LOG_LEVEL_INFO, "Integration completed successfully or with acceptable termination code: (%d).", err);

            err = NO_ERROR;
            err = BaseTrajSeq_t_get_at(&result, KEY_POS_X, target_x_ft, -1, &hit);
            if (err != NO_ERROR)
            {
                err = Engine_t_ERR(eng, RUNTIME_ERROR, "Failed to interpolate trajectory at target distance, error code: %d", err);
                goto finally;
            }
        }
        else
        {
            err = Engine_t_ERR(eng, err, "Critical: integration error: %s, error code: %d", eng->err_msg, err);
            goto finally;
        }
        if (hit.time == 0.0)
        {
            // Integrator returned initial point - consider removing constraints
            break;
        }
        current_distance = hit.position.x;
        if (2 * current_distance < target_x_ft && eng->shot.barrel_elevation == 0.0 && look_angle_rad < 1.5)
        {
            // Degenerate case: little distance and zero elevation; try with some elevation
            eng->shot.barrel_elevation = 0.01;
            continue;
        }

        ca = cos(look_angle_rad);
        sa = sin(look_angle_rad);
        height_diff_ft = hit.position.y * ca - hit.position.x * sa; // slant_height
        look_dist_ft = hit.position.x * ca + hit.position.y * sa;   // slant_distance
        range_diff_ft = look_dist_ft - slant_range_ft;
        range_error_ft = fabs(range_diff_ft);
        height_error_ft = fabs(height_diff_ft);
        trajectory_angle = atan2(hit.velocity.y, hit.velocity.x); // Flight angle at current distance

        // Calculate sensitivity and correction
        sensitivity = (tan(eng->shot.barrel_elevation - look_angle_rad) * tan(trajectory_angle - look_angle_rad));
        if (sensitivity < -0.5)
        {
            denominator = look_dist_ft;
        }
        else
        {
            denominator = look_dist_ft * (1 + sensitivity);
        }

        if (fabs(denominator) > 1e-9)
        {
            correction = -height_diff_ft / denominator;
        }
        else
        {
            zero_error->zero_finding_error = height_error_ft;
            zero_error->iterations_count = iterations_count;
            zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
            err = Engine_t_ERR(eng, ZERO_FINDING_ERROR, "Correction denominator is zero");
            goto finally;
        }

        if (range_error_ft > ALLOWED_ZERO_ERROR_FEET)
        {
            // We're still trying to reach zero_distance
            // We're not getting closer to zero_distance
            if (range_error_ft > prev_range_error_ft - 1e-6)
            {
                zero_error->zero_finding_error = range_error_ft;
                zero_error->iterations_count = iterations_count;
                zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
                err = Engine_t_ERR(eng, ZERO_FINDING_ERROR, "Distance non-convergent");
                goto finally;
            }
        }
        else if (height_error_ft > fabs(prev_height_error_ft))
        {
            damping_factor *= damping_rate;
            if (damping_factor < 0.3)
            {
                zero_error->zero_finding_error = height_error_ft;
                zero_error->iterations_count = iterations_count;
                zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
                err = Engine_t_ERR(eng, ZERO_FINDING_ERROR, "Error non-convergent");
                goto finally;
            }
            // Revert previous adjustment
            eng->shot.barrel_elevation -= last_correction;
            correction = last_correction;
        }
        else if (damping_factor < 1.0)
        {
            damping_factor = 1.0;
        }

        prev_range_error_ft = range_error_ft;
        prev_height_error_ft = height_error_ft;
        if (height_error_ft > _cZeroFindingAccuracy || range_error_ft > ALLOWED_ZERO_ERROR_FEET)
        {
            // Adjust barrel elevation to close height at zero distance
            applied_correction = correction * damping_factor;
            eng->shot.barrel_elevation += applied_correction;
            last_correction = applied_correction;
        }
        else
        {
            // Current barrel_elevation hit zero: success!
            break;
        }
        iterations_count++;
    }

finally:
    // Restore original constraints
    if (has_restore_cMaximumDrop)
    {
        eng->config.cMaximumDrop = restore_cMaximumDrop;
    }
    if (has_restore_cMinimumAltitude)
    {
        eng->config.cMinimumAltitude = restore_cMinimumAltitude;
    }

    if (height_error_ft > _cZeroFindingAccuracy || range_error_ft > ALLOWED_ZERO_ERROR_FEET)
    {
        // ZeroFindingError contains an instance of last barrel elevation;
        // so caller can check how close zero is
        zero_error->zero_finding_error = height_error_ft;
        zero_error->iterations_count = iterations_count;
        zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
        err = Engine_t_ERR(eng, ZERO_FINDING_ERROR, "");
    }

    if (err == ZERO_FINDING_ERROR)
    {
    }

    // success
    *result = eng->shot.barrel_elevation;
    return NO_ERROR;
};