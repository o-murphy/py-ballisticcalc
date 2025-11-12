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
    BCLIBC_BaseTrajSeq *trajectory,
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

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_ENGINE_H
