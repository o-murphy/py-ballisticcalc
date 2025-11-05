#include "bclibc_engine.h"

/*
Possible call chains:

BCLIBC_EngineT_findZeroAngle
 ├─> BCLIBC_EngineT_initZeroCalculation
 │    └─> BCLIBC_EngineT_findApex
 │         └─> BCLIBC_EngineT_integrate
 │              └─> eng->integrate_func_ptr
 ├─> BCLIBC_EngineT_findMaxRange
 │    ├─> BCLIBC_EngineT_findApex
 │    │    └─> BCLIBC_EngineT_integrate
 │    │         └─> eng->integrate_func_ptr
 │    └─> BCLIBC_EngineT_rangeForAngle
 │         └─> BCLIBC_EngineT_integrate
 │              └─> eng->integrate_func_ptr
 └─> BCLIBC_EngineT_errorAtDistance
      └─> BCLIBC_EngineT_integrate
      └─> BCLIBC_BaseTrajSeq_getAt / get_raw_item

BCLIBC_EngineT_zeroAngle
 ├─> BCLIBC_EngineT_initZeroCalculation
 ├─> BCLIBC_EngineT_integrate
 └─> BCLIBC_BaseTrajSeq_init / get_at / release

 Longest callstack:

 BCLIBC_EngineT_findZeroAngle
 -> BCLIBC_EngineT_initZeroCalculation
    -> BCLIBC_EngineT_findApex
       -> BCLIBC_EngineT_integrate
          -> eng->integrate_func_ptr
*/

void BCLIBC_requireNonNullFatal(const void *ptr, const char *file, int line, const char *func)
{
    if (!ptr)
    {
        fprintf(stderr, "FATAL: NULL pointer at %s:%d in %s\n", file, line, func);
        fflush(stderr);
        abort();
    }
}

void BCLIBC_EngineT_releaseTrajectory(BCLIBC_EngineT *eng)
{
    if (eng == NULL)
    {
        return;
    }
    BCLIBC_ShotProps_release(&eng->shot);
    // NOTE: It is not neccessary to NULLIFY integrate_func_ptr
}

BCLIBC_StatusCode BCLIBC_EngineT_integrate(
    BCLIBC_EngineT *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    BCLIBC_TrajFlag filter_flags,
    BCLIBC_BaseTrajSeq *traj_seq_ptr,
    BCLIBC_TerminationReason *reason)
{
    if (!eng || !traj_seq_ptr || !reason || !eng->integrate_func_ptr)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_INTEGRATE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }
    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Using integration function pointer %p.", (void *)eng->integrate_func_ptr);

    BCLIBC_StatusCode status = eng->integrate_func_ptr(eng, range_limit_ft, range_step_ft, time_step, filter_flags, traj_seq_ptr, reason);

    if (status != BCLIBC_STATUS_ERROR)
    {
        if (*reason == BCLIBC_TERM_REASON_NO_TERMINATE)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_INFO, "Integration completed successfully: (%d).", *reason);
        }
        else
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_INFO, "Integration completed with acceptable termination reason: (%d).", *reason);
        }
        BCLIBC_LOG(
            BCLIBC_LOG_LEVEL_DEBUG,
            "Dense buffer length/capacity: %zu/%zu, Size: %zu bytes",
            traj_seq_ptr->length, traj_seq_ptr->capacity,
            traj_seq_ptr->length * sizeof(BCLIBC_BaseTraj));
        return BCLIBC_STATUS_SUCCESS;
    }

    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_INTEGRATE, "Integration failed");
    return BCLIBC_STATUS_ERROR;
}

BCLIBC_StatusCode BCLIBC_EngineT_findApex(BCLIBC_EngineT *eng, BCLIBC_BaseTrajData *out)
{
    if (!eng || !out)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_FIND_APEX, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    if (eng->shot.barrel_elevation <= 0)
    {
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_VALUE_ERROR, BCLIBC_SRC_FIND_APEX, "Value error (Barrel elevation must be greater than 0 to find apex).");
        return BCLIBC_STATUS_ERROR;
    }

    // Have to ensure cMinimumVelocity is 0 for this to work
    double restore_min_velocity = 0.0;
    int has_restore_min_velocity = 0;
    BCLIBC_BaseTrajSeq result;
    BCLIBC_StatusCode status;

    BCLIBC_BaseTrajSeq_init(&result);

    if (eng->config.cMinimumVelocity > 0.0)
    {
        restore_min_velocity = eng->config.cMinimumVelocity;
        eng->config.cMinimumVelocity = 0.0;
        has_restore_min_velocity = 1;
    }

    // try
    BCLIBC_TerminationReason reason;
    status = BCLIBC_EngineT_integrate(eng, 9e9, 9e9, 0.0, BCLIBC_TRAJ_FLAG_APEX, &result, &reason);

    if (status != BCLIBC_STATUS_SUCCESS)
    {
        status = BCLIBC_STATUS_ERROR;
    }
    else
    {
        status = BCLIBC_BaseTrajSeq_getAt(&result, BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y, 0.0, -1, out);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_FIND_APEX, "Runtime error (No apex flagged in trajectory data)");
            status = BCLIBC_STATUS_ERROR;
        }
        else
        {
            status = BCLIBC_STATUS_SUCCESS;
        }
    }
    // finally
    if (has_restore_min_velocity)
    {
        eng->config.cMinimumVelocity = restore_min_velocity;
    }

    BCLIBC_BaseTrajSeq_release(&result);
    return status;
}

BCLIBC_StatusCode BCLIBC_EngineT_errorAtDistance(
    BCLIBC_EngineT *eng,
    double angle_rad,
    double target_x_ft,
    double target_y_ft,
    double *out_error_ft)
{
    *out_error_ft = 9e9;

    if (!eng || !out_error_ft)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_ERROR_AT_DISTANCE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    BCLIBC_BaseTrajSeq trajectory;
    BCLIBC_BaseTrajData hit;
    BCLIBC_BaseTraj *last_ptr;

    BCLIBC_BaseTrajSeq_init(&trajectory);

    // try

    eng->shot.barrel_elevation = angle_rad;

    BCLIBC_TerminationReason reason;
    BCLIBC_StatusCode status = BCLIBC_EngineT_integrate(eng, 9e9, 9e9, 0.0, BCLIBC_TRAJ_FLAG_APEX, &trajectory, &reason);

    if (status != BCLIBC_STATUS_SUCCESS)
    {
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_ERROR_AT_DISTANCE, "Find apex error");
    }
    else
    {
        // If trajectory is too short for cubic interpolation, treat as unreachable
        if (trajectory.length >= 3)
        {
            last_ptr = BCLIBC_BaseTrajSeq_getRawItem(&trajectory, -1);
            if (last_ptr != NULL && last_ptr->time != 0.0)
            {
                status = BCLIBC_BaseTrajSeq_getAt(&trajectory, BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X, target_x_ft, -1, &hit);
                if (status != BCLIBC_STATUS_SUCCESS)
                {
                    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_ERROR_AT_DISTANCE, "Runtime error (No apex flagged in trajectory data)");
                    status = BCLIBC_STATUS_ERROR;
                }
                else
                {
                    *out_error_ft = (hit.position.y - target_y_ft) - fabs(hit.position.x - target_x_ft);
                    status = BCLIBC_STATUS_SUCCESS;
                }
            }
            else
            {
                BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_ERROR_AT_DISTANCE, "Trajectory sequence error, error code: %d", status);
                status = BCLIBC_STATUS_ERROR;
            }
        }
    }

    // finally:
    BCLIBC_BaseTrajSeq_release(&trajectory);
    return status;
};

BCLIBC_StatusCode BCLIBC_EngineT_initZeroCalculation(
    BCLIBC_EngineT *eng,
    double distance,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    BCLIBC_ZeroInitialData *result,
    BCLIBC_OutOfRangeError *error)
{

    if (!eng || !result || !error)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_INIT_ZERO, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    BCLIBC_StatusCode status;
    BCLIBC_BaseTrajData apex;
    double apex_slant_ft;

    result->status = BCLIBC_ZERO_INIT_DONE;
    result->slant_range_ft = distance;
    result->look_angle_rad = eng->shot.look_angle;
    result->target_x_ft = result->slant_range_ft * cos(result->look_angle_rad);
    result->target_y_ft = result->slant_range_ft * sin(result->look_angle_rad);
    result->start_height_ft = -eng->shot.sight_height * eng->shot.cant_cosine;

    // Edge case: Very close shot
    if (fabs(result->slant_range_ft) < ALLOWED_ZERO_ERROR_FEET)
    {
        return BCLIBC_STATUS_SUCCESS;
    }

    // Edge case: Very close shot; ignore gravity and drag
    if (fabs(result->slant_range_ft) < 2.0 * fmax(fabs(result->start_height_ft),
                                                  eng->config.cStepMultiplier))
    {
        result->look_angle_rad = atan2(result->target_y_ft + result->start_height_ft, result->target_x_ft);
        return BCLIBC_STATUS_SUCCESS;
    }

    // Edge case: Virtually vertical shot; just check if it can reach the target
    if (fabs(result->look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
    {
        // Compute slant distance at apex using robust accessor
        status = BCLIBC_EngineT_findApex(eng, &apex);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            return BCLIBC_STATUS_ERROR; // Redirect apex finding error
        }
        apex_slant_ft = apex.position.x * cos(result->look_angle_rad) + apex.position.y * sin(result->look_angle_rad);
        if (apex_slant_ft < result->slant_range_ft)
        {
            error->requested_distance_ft = result->slant_range_ft;
            error->max_range_ft = apex_slant_ft;
            error->look_angle_rad = result->look_angle_rad;
            BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_OUT_OF_RANGE_ERROR, BCLIBC_SRC_INIT_ZERO, "Out of range");
            return BCLIBC_STATUS_ERROR;
        }
        return BCLIBC_STATUS_SUCCESS;
    }

    result->status = BCLIBC_ZERO_INIT_CONTINUE;
    return BCLIBC_STATUS_SUCCESS;
}

BCLIBC_StatusCode BCLIBC_EngineT_zeroAngleWithFallback(
    BCLIBC_EngineT *eng,
    double distance,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    double *result,
    BCLIBC_OutOfRangeError *range_error,
    BCLIBC_ZeroFindingError *zero_error)
{
    if (!eng || !result || !range_error || !zero_error)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    BCLIBC_StatusCode status;

    status = BCLIBC_EngineT_zeroAngle(eng, distance, APEX_IS_MAX_RANGE_RADIANS, ALLOWED_ZERO_ERROR_FEET, result, range_error, zero_error);
    if (status == BCLIBC_STATUS_SUCCESS)
    {
        return BCLIBC_STATUS_SUCCESS;
    }
    BCLIBC_LOG(BCLIBC_LOG_LEVEL_WARNING, "Primary zero-finding failed, switching to fallback.");

    // Clean error stack
    BCLIBC_CLEAR_ERR(&eng->err_stack);

    // Fallback to guaranteed method
    int lofted = 0; // default

    status = BCLIBC_EngineT_findZeroAngle(eng, distance, APEX_IS_MAX_RANGE_RADIANS, ALLOWED_ZERO_ERROR_FEET, lofted, result, range_error, zero_error);
    if (status == BCLIBC_STATUS_SUCCESS)
    {
        return BCLIBC_STATUS_SUCCESS;
    }

    // Return error if no found
    return BCLIBC_STATUS_ERROR;
}

BCLIBC_StatusCode BCLIBC_EngineT_zeroAngle(
    BCLIBC_EngineT *eng,
    double distance,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    double *result,
    BCLIBC_OutOfRangeError *range_error,
    BCLIBC_ZeroFindingError *zero_error)
{
    if (!eng || !result || !range_error || !zero_error)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    BCLIBC_ZeroInitialData init_data;
    BCLIBC_StatusCode status = BCLIBC_EngineT_initZeroCalculation(
        eng,
        distance,
        APEX_IS_MAX_RANGE_RADIANS,
        ALLOWED_ZERO_ERROR_FEET,
        &init_data,
        range_error); // pass pointer directly, not &range_error

    if (status != BCLIBC_STATUS_SUCCESS)
    {
        return BCLIBC_STATUS_ERROR;
    }

    double look_angle_rad = init_data.look_angle_rad;
    double slant_range_ft = init_data.slant_range_ft;
    double target_x_ft = init_data.target_x_ft;
    double target_y_ft = init_data.target_y_ft;

    if (init_data.status == BCLIBC_ZERO_INIT_DONE)
    {
        *result = look_angle_rad;
        return BCLIBC_STATUS_SUCCESS; // immediately return when already done
    }

    BCLIBC_BaseTrajData hit;
    BCLIBC_BaseTrajSeq seq;
    status = BCLIBC_STATUS_SUCCESS; // initialize
    BCLIBC_BaseTrajSeq_init(&seq);

    double _cZeroFindingAccuracy = eng->config.cZeroFindingAccuracy;
    int _cMaxIterations = eng->config.cMaxIterations;

    int iterations_count = 0;
    double range_error_ft = 9e9;
    double prev_range_error_ft = 9e9;
    double prev_height_error_ft = 9e9;
    double damping_factor = 1.0;
    double damping_rate = 0.7;
    double last_correction = 0.0;
    double height_error_ft = _cZeroFindingAccuracy * 2;

    double required_drop_ft = target_x_ft / 2.0 - target_y_ft;
    double restore_cMaximumDrop = 0.0;
    double restore_cMinimumAltitude = 0.0;
    int has_restore_cMaximumDrop = 0;
    int has_restore_cMinimumAltitude = 0;

    double current_distance = 0.0;
    double trajectory_angle = 0.0;

    // Backup and adjust constraints if needed
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

    // Main iteration loop
    while (iterations_count < _cMaxIterations)
    {
        // reset seq for integration result
        BCLIBC_BaseTrajSeq_release(&seq);
        BCLIBC_BaseTrajSeq_init(&seq);

        BCLIBC_TerminationReason reason;
        status = BCLIBC_EngineT_integrate(eng, target_x_ft, target_x_ft, 0.0, BCLIBC_TRAJ_FLAG_NONE, &seq, &reason);

        if (status != BCLIBC_STATUS_SUCCESS)
        {
            status = BCLIBC_STATUS_ERROR;
            break;
        }

        // interpolate trajectory at target_x_ft using the sequence we just filled
        status = BCLIBC_BaseTrajSeq_getAt(&seq, BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X, target_x_ft, -1, &hit); // <--- FIXED: pass &seq, not &result
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_RUNTIME_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Failed to interpolate trajectory at target distance");
            status = BCLIBC_STATUS_SUCCESS;
            break;
        }

        if (hit.time == 0.0)
        {
            // Integrator returned initial point - consider removing constraints / bail out
            break;
        }

        current_distance = hit.position.x;
        if (2 * current_distance < target_x_ft && eng->shot.barrel_elevation == 0.0 && look_angle_rad < 1.5)
        {
            eng->shot.barrel_elevation = 0.01;
            iterations_count++;
            continue;
        }

        double ca = cos(look_angle_rad);
        double sa = sin(look_angle_rad);
        double height_diff_ft = hit.position.y * ca - hit.position.x * sa;
        double look_dist_ft = hit.position.x * ca + hit.position.y * sa;
        double range_diff_ft = look_dist_ft - slant_range_ft;
        range_error_ft = fabs(range_diff_ft);
        height_error_ft = fabs(height_diff_ft);
        trajectory_angle = atan2(hit.velocity.y, hit.velocity.x);

        double sensitivity = (tan(eng->shot.barrel_elevation - look_angle_rad) * tan(trajectory_angle - look_angle_rad));
        double denominator;
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
            double correction = -height_diff_ft / denominator;

            if (range_error_ft > ALLOWED_ZERO_ERROR_FEET)
            {
                if (range_error_ft > prev_range_error_ft - 1e-6)
                {
                    zero_error->zero_finding_error = range_error_ft;
                    zero_error->iterations_count = iterations_count;
                    zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
                    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Distance non-convergent");
                    status = BCLIBC_STATUS_ERROR;
                    break;
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
                    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Error non-convergent");
                    status = BCLIBC_STATUS_ERROR;
                    break;
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
                double applied_correction = correction * damping_factor;
                eng->shot.barrel_elevation += applied_correction;
                last_correction = applied_correction;
            }
            else
            {
                // success
                break;
            }
        }
        else
        {
            zero_error->zero_finding_error = height_error_ft;
            zero_error->iterations_count = iterations_count;
            zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
            BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Correction denominator is zero");
            status = BCLIBC_STATUS_ERROR;
            break;
        }

        iterations_count++;
    }

    // finally:

    // Always release seq if it was allocated
    BCLIBC_BaseTrajSeq_release(&seq);

    // Restore original constraints
    if (has_restore_cMaximumDrop)
    {
        eng->config.cMaximumDrop = restore_cMaximumDrop;
    }
    if (has_restore_cMinimumAltitude)
    {
        eng->config.cMinimumAltitude = restore_cMinimumAltitude;
    }

    if (status != BCLIBC_STATUS_SUCCESS)
    {
        // Fill zero_error if not already filled
        zero_error->zero_finding_error = height_error_ft;
        zero_error->iterations_count = iterations_count;
        zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_ZERO_ANGLE, "Zero finding error");
        return BCLIBC_STATUS_ERROR;
    }

    // success
    *result = eng->shot.barrel_elevation;
    return BCLIBC_STATUS_SUCCESS;
}

// Returns max slant-distance for given launch angle in radians.
// Robust ZERO_DOWN detection: scan from the end and find the first slant-height
// crossing where the previous point is positive and current is non-positive.
static BCLIBC_StatusCode BCLIBC_EngineT_rangeForAngle(BCLIBC_EngineT *eng, double angle_rad, double *result)
{
    if (!eng || !result)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_RANGE_FOR_ANGLE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    double ca;
    double sa;
    double h_prev;
    double h_cur;
    double denom;
    double t;
    double ix;
    double iy;
    double sdist;
    BCLIBC_BaseTrajSeq trajectory;
    BCLIBC_StatusCode status;
    ssize_t n;
    ssize_t i;
    BCLIBC_BaseTraj *prev_ptr;
    BCLIBC_BaseTraj *cur_ptr;

    // Update shot data
    eng->shot.barrel_elevation = angle_rad;

    // try:
    *result = -9e9;
    BCLIBC_BaseTrajSeq_init(&trajectory);

    BCLIBC_TerminationReason reason;
    status = BCLIBC_EngineT_integrate(eng, 9e9, 9e9, 0.0, BCLIBC_TRAJ_FLAG_NONE, &trajectory, &reason);
    if (status != BCLIBC_STATUS_SUCCESS)
    {
        status = BCLIBC_STATUS_ERROR;
    }
    else
    {
        ca = cos(eng->shot.look_angle);
        sa = sin(eng->shot.look_angle);
        n = trajectory.length;
        if (n >= 2)
        {
            // Linear search from end of trajectory for zero-down crossing
            for (i = n - 1; i > 0; i--)
            {
                prev_ptr = BCLIBC_BaseTrajSeq_getRawItem(&trajectory, i - 1);
                if (prev_ptr == NULL)
                {
                    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INDEX_ERROR, BCLIBC_SRC_RANGE_FOR_ANGLE, "Index error in BCLIBC_BaseTrajSeq_getRawItem");
                    status = BCLIBC_STATUS_ERROR;
                    break; // assume INDEX_ERROR
                }
                cur_ptr = BCLIBC_BaseTrajSeq_getRawItem(&trajectory, i);
                if (cur_ptr == NULL)
                {
                    BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INDEX_ERROR, BCLIBC_SRC_RANGE_FOR_ANGLE, "Index error in BCLIBC_BaseTrajSeq_getRawItem");
                    status = BCLIBC_STATUS_ERROR;
                    break; // assume INDEX_ERROR
                }
                h_prev = prev_ptr->py * ca - prev_ptr->px * sa;
                h_cur = cur_ptr->py * ca - cur_ptr->px * sa;
                if (h_prev > 0.0 && h_cur <= 0.0)
                {
                    // Interpolate for slant_distance
                    denom = h_prev - h_cur;
                    t = denom == 0.0 ? 0.0 : h_prev / denom;
                    t = fmax(0.0, fmin(1.0, t));
                    ix = prev_ptr->px + t * (cur_ptr->px - prev_ptr->px);
                    iy = prev_ptr->py + t * (cur_ptr->py - prev_ptr->py);
                    sdist = ix * ca + iy * sa;
                    *result = sdist;
                    status = BCLIBC_STATUS_SUCCESS;
                    break;
                }
            }
        }
    }

    BCLIBC_BaseTrajSeq_release(&trajectory);
    return status;
}

BCLIBC_StatusCode BCLIBC_EngineT_findMaxRange(
    BCLIBC_EngineT *eng,
    double low_angle_deg,
    double high_angle_deg,
    double APEX_IS_MAX_RANGE_RADIANS,
    BCLIBC_MaxRangeResult *result)
{

    if (!eng || !result)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_FIND_MAX_RANGE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    double look_angle_rad = eng->shot.look_angle;
    double max_range_ft;
    double angle_at_max_rad;
    BCLIBC_BaseTrajData apex;
    BCLIBC_StatusCode status;
    double sdist;

    // Backup and adjust constraints (emulate @with_max_drop_zero and @with_no_minimum_velocity)
    double restore_cMaximumDrop = 0.0;
    int has_restore_cMaximumDrop = 0;
    double restore_cMinimumVelocity = 0.0;
    int has_restore_cMinimumVelocity = 0;

    // Virtually vertical shot
    // π/2 radians = 90 degrees
    if (fabs(look_angle_rad - 1.5707963267948966) < APEX_IS_MAX_RANGE_RADIANS)
    {
        status = BCLIBC_EngineT_findApex(eng, &apex);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            return BCLIBC_STATUS_ERROR; // Redirect apex finding error
        }
        sdist = apex.position.x * cos(look_angle_rad) + apex.position.y * sin(look_angle_rad);
        result->max_range_ft = sdist;
        result->angle_at_max_rad = look_angle_rad;
        return BCLIBC_STATUS_SUCCESS;
    }

    if (eng->config.cMaximumDrop != 0.0)
    {
        restore_cMaximumDrop = eng->config.cMaximumDrop;
        eng->config.cMaximumDrop = 0.0; // We want to run trajectory until it returns to horizontal
        has_restore_cMaximumDrop = 1;
    }

    if (eng->config.cMinimumVelocity != 0.0)
    {
        restore_cMinimumVelocity = eng->config.cMinimumVelocity;
        eng->config.cMinimumVelocity = 0.0; // We want to run trajectory until it returns to horizontal
        has_restore_cMinimumVelocity = 1;
    }

    double inv_phi = 0.6180339887498949;              // (sqrt(5) - 1) / 2
    double inv_phi_sq = 0.38196601125010515;          // inv_phi^2
    double a = low_angle_deg * 0.017453292519943295;  // Convert to radians
    double b = high_angle_deg * 0.017453292519943295; // Convert to radians
    double h = b - a;
    double c = a + inv_phi_sq * h;
    double d = a + inv_phi * h;
    double yc, yd;

    BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, c, &yc);
    BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, d, &yd);

    // Golden-section search
    for (int i = 0; i < 100; i++)
    {
        if (h < 1e-5)
        {
            break;
        }
        if (yc > yd)
        {
            b = d;
            d = c;
            yd = yc;
            h = b - a;
            c = a + inv_phi_sq * h;
            BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, c, &yc);
        }
        else
        {
            a = c;
            c = d;
            yc = yd;
            h = b - a;
            d = a + inv_phi * h;
            BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, d, &yd);
        }
    }

    angle_at_max_rad = (a + b) / 2;
    BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, angle_at_max_rad, &max_range_ft);

    // Restore original constraints
    if (has_restore_cMaximumDrop)
    {
        eng->config.cMaximumDrop = restore_cMaximumDrop;
    }
    if (has_restore_cMinimumVelocity)
    {
        eng->config.cMinimumVelocity = restore_cMinimumVelocity;
    }

    result->max_range_ft = max_range_ft;
    result->angle_at_max_rad = angle_at_max_rad;
    return BCLIBC_STATUS_SUCCESS;
}

BCLIBC_StatusCode BCLIBC_EngineT_findZeroAngle(
    BCLIBC_EngineT *eng,
    double distance,
    int lofted,
    double APEX_IS_MAX_RANGE_RADIANS,
    double ALLOWED_ZERO_ERROR_FEET,
    double *result,
    BCLIBC_OutOfRangeError *range_error,
    BCLIBC_ZeroFindingError *zero_error)
{

    if (!eng || !result || !range_error || !zero_error)
    {
        REQUIRE_NON_NULL(eng);
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_FIND_ZERO_ANGLE, "Invalid input (NULL pointer).");
        return BCLIBC_STATUS_ERROR;
    }

    BCLIBC_ZeroInitialData init_data;
    BCLIBC_StatusCode status = BCLIBC_EngineT_initZeroCalculation(
        eng,
        distance,
        APEX_IS_MAX_RANGE_RADIANS,
        ALLOWED_ZERO_ERROR_FEET,
        &init_data,
        range_error);

    if (status != BCLIBC_STATUS_SUCCESS)
    {
        return BCLIBC_STATUS_ERROR;
    }

    double look_angle_rad = init_data.look_angle_rad;
    double slant_range_ft = init_data.slant_range_ft;
    double target_x_ft = init_data.target_x_ft;
    double target_y_ft = init_data.target_y_ft;
    double start_height_ft = init_data.start_height_ft;

    if (init_data.status == BCLIBC_ZERO_INIT_DONE)
    {
        *result = look_angle_rad;
        return BCLIBC_STATUS_SUCCESS;
    }

    // 1. Find the maximum possible range to establish a search bracket.
    BCLIBC_MaxRangeResult max_range_result;
    status = BCLIBC_EngineT_findMaxRange(
        eng,
        0,
        90,
        APEX_IS_MAX_RANGE_RADIANS,
        &max_range_result);
    if (status != BCLIBC_STATUS_SUCCESS)
    {
        return BCLIBC_STATUS_ERROR;
    }

    double max_range_ft = max_range_result.max_range_ft;
    double angle_at_max_rad = max_range_result.angle_at_max_rad;

    // 2. Handle edge cases based on max range.
    if (slant_range_ft > max_range_ft)
    {
        range_error->requested_distance_ft = distance;
        range_error->max_range_ft = max_range_ft;
        range_error->look_angle_rad = look_angle_rad;
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_OUT_OF_RANGE_ERROR, BCLIBC_SRC_FIND_ZERO_ANGLE, "Out of range");
        return BCLIBC_STATUS_ERROR;
    }
    if (fabs(slant_range_ft - max_range_ft) < ALLOWED_ZERO_ERROR_FEET)
    {
        *result = angle_at_max_rad;
        return BCLIBC_STATUS_SUCCESS;
    }

    // Backup and adjust constraints (emulate @with_no_minimum_velocity)
    double restore_cMinimumVelocity__zero = 0.0;
    int has_restore_cMinimumVelocity__zero = 0;
    if (eng->config.cMinimumVelocity != 0.0)
    {
        restore_cMinimumVelocity__zero = eng->config.cMinimumVelocity;
        eng->config.cMinimumVelocity = 0.0;
        has_restore_cMinimumVelocity__zero = 1;
    }

    // 3. Establish search bracket for the zero angle.
    double low_angle, high_angle;
    double sight_height_adjust = 0.0;
    double f_low, f_high;

    if (lofted)
    {
        low_angle = angle_at_max_rad;
        high_angle = 1.5690308719637473; // 89.9 degrees in radians
    }
    else
    {
        if (start_height_ft > 0.0)
        {
            sight_height_adjust = atan2(start_height_ft, target_x_ft);
        }
        low_angle = look_angle_rad - sight_height_adjust;
        high_angle = angle_at_max_rad;
    }

    // Prepare variables for Ridder's method
    double mid_angle, f_mid, s, next_angle, f_next;
    int converged = 0;

    status = BCLIBC_EngineT_errorAtDistance(
        eng,
        low_angle,
        target_x_ft,
        target_y_ft,
        &f_low);
    if (status != BCLIBC_STATUS_SUCCESS)
    {
        goto finally;
    }

    // If low is exactly look angle and failed to evaluate, nudge slightly upward to bracket
    if (f_low > 1e8 && fabs(low_angle - look_angle_rad) < 1e-9)
    {
        low_angle = look_angle_rad + 1e-3;
        status = BCLIBC_EngineT_errorAtDistance(
            eng,
            low_angle,
            target_x_ft,
            target_y_ft,
            &f_low);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            goto finally;
        }
    }

    status = BCLIBC_EngineT_errorAtDistance(
        eng,
        high_angle,
        target_x_ft,
        target_y_ft,
        &f_high);
    if (status != BCLIBC_STATUS_SUCCESS)
    {
        goto finally;
    }

    if (f_low * f_high >= 0)
    {
        char reason[256];
        const char *lofted_str = lofted ? "lofted" : "low";
        snprintf(
            reason,
            sizeof(reason),
            "No %s zero trajectory in elevation range (%.2f, %.2f deg). "
            "Errors at bracket: f(low)=%.2f, f(high)=%.2f",
            lofted_str,
            low_angle * 57.29577951308232,
            high_angle * 57.29577951308232,
            f_low,
            f_high);
        zero_error->zero_finding_error = target_y_ft;
        zero_error->iterations_count = 0;
        zero_error->last_barrel_elevation_rad = eng->shot.barrel_elevation;
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_FIND_ZERO_ANGLE, reason);
        status = BCLIBC_STATUS_ERROR;
        goto finally;
    }

    // 4. Ridder's method implementation
    for (int i = 0; i < eng->config.cMaxIterations; i++)
    {
        mid_angle = (low_angle + high_angle) / 2.0;

        status = BCLIBC_EngineT_errorAtDistance(
            eng,
            mid_angle,
            target_x_ft,
            target_y_ft,
            &f_mid);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            goto finally;
        }

        // Check if we found exact solution at midpoint
        if (fabs(f_mid) < eng->config.cZeroFindingAccuracy)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: found exact solution at mid_angle=%.6f", mid_angle);
            *result = mid_angle;
            converged = 1;
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }

        // s is the updated point using the root of the linear function
        // through (low_angle, f_low) and (high_angle, f_high)
        // and the quadratic function that passes through those points and (mid_angle, f_mid)
        double _inner = f_mid * f_mid - f_low * f_high;

        BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG,
                   "Ridder iteration %d: low_angle=%.12f, high_angle=%.12f, mid_angle=%.12f, "
                   "f_low=%.12f, f_high=%.12f, f_mid=%.12f, _inner=%.12e",
                   i, low_angle, high_angle, mid_angle, f_low, f_high, f_mid, _inner);

        // Check for invalid sqrt argument - should not happen if bracket is valid
        if (_inner <= 0.0)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: _inner <= 0 (%.12e), breaking iteration", _inner);
            break;
        }

        s = sqrt(_inner);

        // Should not happen if f_low and f_high have opposite signs
        if (s == 0.0)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: s == 0, breaking iteration");
            break;
        }

        next_angle = mid_angle + (mid_angle - low_angle) * (copysign(1.0, f_low - f_high) * f_mid / s);

        if (fabs(next_angle - mid_angle) < eng->config.cZeroFindingAccuracy)
        {
            *result = next_angle;
            converged = 1;
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }

        status = BCLIBC_EngineT_errorAtDistance(
            eng,
            next_angle,
            target_x_ft,
            target_y_ft,
            &f_next);
        if (status != BCLIBC_STATUS_SUCCESS)
        {
            goto finally;
        }

        // Check if we found exact solution at next_angle
        if (fabs(f_next) < eng->config.cZeroFindingAccuracy)
        {
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: found exact solution at next_angle=%.6f", next_angle);
            *result = next_angle;
            converged = 1;
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }

        // Update the bracket
        if (f_mid * f_next < 0)
        {
            low_angle = mid_angle;
            f_low = f_mid;
            high_angle = next_angle;
            f_high = f_next;
        }
        else if (f_low * f_next < 0)
        {
            high_angle = next_angle;
            f_high = f_next;
        }
        else if (f_high * f_next < 0)
        {
            low_angle = next_angle;
            f_low = f_next;
        }
        else
        {
            // If we are here, something is wrong, the root is not bracketed anymore
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: root not bracketed anymore, breaking");
            break;
        }

        if (fabs(high_angle - low_angle) < eng->config.cZeroFindingAccuracy)
        {
            *result = (low_angle + high_angle) / 2.0;
            converged = 1;
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }
    }

    // If we exited the loop without convergence
    if (!converged)
    {
        // Try fallback strategies before giving up

        // If we have a very small bracket, consider it converged
        if (fabs(high_angle - low_angle) < 10.0 * eng->config.cZeroFindingAccuracy)
        {
            *result = (low_angle + high_angle) / 2.0;
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: accepting solution from small bracket: %.6f", *result);
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }

        // If we have very small errors, consider it converged
        if (fabs(f_low) < 10.0 * eng->config.cZeroFindingAccuracy)
        {
            *result = low_angle;
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: accepting low_angle due to small f_low: %.6f", *result);
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }
        if (fabs(f_high) < 10.0 * eng->config.cZeroFindingAccuracy)
        {
            *result = high_angle;
            BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Ridder: accepting high_angle due to small f_high: %.6f", *result);
            status = BCLIBC_STATUS_SUCCESS;
            goto finally;
        }

        // All fallback strategies failed
        zero_error->zero_finding_error = target_y_ft;
        zero_error->iterations_count = eng->config.cMaxIterations;
        zero_error->last_barrel_elevation_rad = (low_angle + high_angle) / 2.0;
        BCLIBC_PUSH_ERR(&eng->err_stack, BCLIBC_E_ZERO_FINDING_ERROR, BCLIBC_SRC_FIND_ZERO_ANGLE, "Ridder's method failed to converge.");
        status = BCLIBC_STATUS_ERROR;
    }

finally:
    if (has_restore_cMinimumVelocity__zero)
    {
        eng->config.cMinimumVelocity = restore_cMinimumVelocity__zero;
    }
    return status;
}
