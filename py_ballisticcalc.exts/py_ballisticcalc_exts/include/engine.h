#ifndef BCLIB_ENGINE_H
#define BCLIB_ENGINE_H

#include "v3d.h"
#include "bclib.h"
#include "base_traj_seq.h"
#include "error_stack.h"

#include <math.h>
#include <stdarg.h> // for va_list, va_start, va_end, va_copy
#include <stdio.h>  // for fprintf
#include <string.h> // for vsnprintf

typedef enum
{
    ZERO_INIT_CONTINUE,
    ZERO_INIT_DONE,
} ZeroInitialStatus;

typedef enum
{
    // Solver specific flags (always include RANGE_ERROR)
    NO_TERMINATE,
    RANGE_ERROR_MINIMUM_VELOCITY_REACHED,
    RANGE_ERROR_MAXIMUM_DROP_REACHED,
    RANGE_ERROR_MINIMUM_ALTITUDE_REACHED,
} TerminationReason;

typedef struct
{
    ZeroInitialStatus status;
    double look_angle_rad;
    double slant_range_ft;
    double target_x_ft;
    double target_y_ft;
    double start_height_ft;
} ZeroInitialData_t;

typedef struct
{
    double requested_distance_ft;
    double max_range_ft;
    double look_angle_rad;
} OutOfRangeError_t;

typedef struct
{
    double max_range_ft;
    double angle_at_max_rad;
} MaxRangeResult_t;

typedef struct
{
    double zero_finding_error;
    int iterations_count;
    double last_barrel_elevation_rad;
} ZeroFindingError_t;

typedef struct Engine_s Engine_t;

typedef StatusCode IntegrateFunc(
    Engine_t *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr,
    TerminationReason *reason);

typedef IntegrateFunc *IntegrateFuncPtr;

typedef struct Engine_s
{
    int integration_step_count;
    V3dT gravity_vector;
    Config_t config;
    ShotProps_t shot;
    IntegrateFuncPtr integrate_func_ptr;
    ErrorStack err_stack;
} Engine_t;

#define Engine_t_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, eng, angle, y_out) \
    do                                                                    \
    {                                                                     \
        (status) = Engine_t_range_for_angle((eng), (angle), (y_out));     \
        if ((status) != STATUS_SUCCESS)                                   \
            return (status);                                              \
    } while (0)

#ifdef __cplusplus
extern "C"
{
#endif

    void Engine_t_release_trajectory(Engine_t *eng);

    StatusCode Engine_t_integrate(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr,
        TerminationReason *reason);

    StatusCode Engine_t_find_apex(Engine_t *eng, BaseTrajData_t *out);

    StatusCode Engine_t_error_at_distance(
        Engine_t *eng,
        double angle_rad,
        double target_x_ft,
        double target_y_ft,
        double *out_error_ft);

    StatusCode Engine_t_init_zero_calculation(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        ZeroInitialData_t *result,
        OutOfRangeError_t *error);

    StatusCode Engine_t_zero_angle(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        OutOfRangeError_t *range_error,
        ZeroFindingError_t *zero_error);

    StatusCode Engine_t_find_max_range(
        Engine_t *eng,
        double low_angle_deg,
        double high_angle_deg,
        double APEX_IS_MAX_RANGE_RADIANS,
        MaxRangeResult_t *result);

    StatusCode Engine_t_find_zero_angle(
        Engine_t *eng,
        double distance,
        int lofted,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        OutOfRangeError_t *range_error,
        ZeroFindingError_t *zero_error);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_ENGINE_H
