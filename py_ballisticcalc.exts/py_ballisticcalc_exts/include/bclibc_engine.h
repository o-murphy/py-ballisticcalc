#ifndef BCLIBC_ENGINE_H
#define BCLIBC_ENGINE_H

#include "bclibc_v3d.h"
#include "bclibc_bclib.h"
#include "bclibc_base_traj_seq.h"
#include "bclibc_error_stack.h"

#include <math.h>
#include <stdarg.h> // for va_list, va_start, va_end, va_copy
#include <stdio.h>  // for fprintf
#include <string.h> // for vsnprintf
#include <stdlib.h> // for abort

typedef enum
{
    BCLIBC_ZERO_INIT_CONTINUE,
    BCLIBC_ZERO_INIT_DONE,
} BCLIBC_ZeroInitialStatus;

typedef enum
{
    // Solver specific flags (always include RANGE_ERROR)
    BCLIBC_TERM_REASON_NO_TERMINATE,
    BCLIBC_TERM_REASON_MINIMUM_VELOCITY_REACHED,
    BCLIBC_TERM_REASON_MAXIMUM_DROP_REACHED,
    BCLIBC_TERM_REASON_MINIMUM_ALTITUDE_REACHED,
} BCLIBC_TerminationReason;

typedef struct
{
    BCLIBC_ZeroInitialStatus status;
    double look_angle_rad;
    double slant_range_ft;
    double target_x_ft;
    double target_y_ft;
    double start_height_ft;
} BCLIBC_ZeroInitialData;

typedef struct
{
    double requested_distance_ft;
    double max_range_ft;
    double look_angle_rad;
} BCLIBC_OutOfRangeError;

typedef struct
{
    double max_range_ft;
    double angle_at_max_rad;
} BCLIBC_MaxRangeResult;

typedef struct
{
    double zero_finding_error;
    int iterations_count;
    double last_barrel_elevation_rad;
} BCLIBC_ZeroFindingError;

typedef struct BCLIBC_EngineS BCLIBC_EngineT;

typedef BCLIBC_StatusCode BCLIBC_IntegrateFunc(
    BCLIBC_EngineT *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    BCLIBC_TrajFlag filter_flags,
    BCLIBC_BaseTrajSeq *traj_seq_ptr,
    BCLIBC_TerminationReason *reason);

typedef BCLIBC_IntegrateFunc *BCLIBC_IntegrateFuncPtr;

typedef struct BCLIBC_EngineS
{
    int integration_step_count;
    BCLIBC_V3dT gravity_vector;
    BCLIBC_Config config;
    BCLIBC_ShotProps shot;
    BCLIBC_IntegrateFuncPtr integrate_func_ptr;
    BCLIBC_ErrorStack err_stack;
} BCLIBC_EngineT;

#ifdef __cplusplus
extern "C"
{
#endif

    void BCLIBC_requireNonNullFatal(const void *ptr, const char *file, int line, const char *func);

    void BCLIBC_EngineT_releaseTrajectory(BCLIBC_EngineT *eng);

    BCLIBC_StatusCode BCLIBC_EngineT_integrate(
        BCLIBC_EngineT *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason);

    BCLIBC_StatusCode BCLIBC_EngineT_findApex(BCLIBC_EngineT *eng, BCLIBC_BaseTrajData *out);

    BCLIBC_StatusCode BCLIBC_EngineT_errorAtDistance(
        BCLIBC_EngineT *eng,
        double angle_rad,
        double target_x_ft,
        double target_y_ft,
        double *out_error_ft);

    BCLIBC_StatusCode BCLIBC_EngineT_initZeroCalculation(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        BCLIBC_ZeroInitialData *result,
        BCLIBC_OutOfRangeError *error);

    BCLIBC_StatusCode BCLIBC_EngineT_zeroAngleWithFallback(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error);

    BCLIBC_StatusCode BCLIBC_EngineT_zeroAngle(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error);

    BCLIBC_StatusCode BCLIBC_EngineT_findMaxRange(
        BCLIBC_EngineT *eng,
        double low_angle_deg,
        double high_angle_deg,
        double APEX_IS_MAX_RANGE_RADIANS,
        BCLIBC_MaxRangeResult *result);

    BCLIBC_StatusCode BCLIBC_EngineT_findZeroAngle(
        BCLIBC_EngineT *eng,
        double distance,
        int lofted,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error);

#ifdef __cplusplus
}
#endif

#define REQUIRE_NON_NULL(ptr) \
    BCLIBC_requireNonNullFatal((ptr), __FILE__, __LINE__, __func__)

#define BCLIBC_EngineT_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, angle, y_out) \
    do                                                                          \
    {                                                                           \
        (status) = BCLIBC_EngineT_rangeForAngle((eng), (angle), (y_out));       \
        if ((status) != BCLIBC_STATUS_SUCCESS)                                  \
            return (status);                                                    \
    } while (0)

#endif // BCLIBC_ENGINE_H
