#ifndef BCLIB_ENGINE_H
#define BCLIB_ENGINE_H

#include "v3d.h"
#include "bclib.h"
#include "base_traj_seq.h"

#include <stdarg.h> // for va_list, va_start, va_end, va_copy
#include <stdio.h>  // for fprintf
#include <string.h> // for vsnprintf

#define MAX_ERR_MSG_LEN 256

typedef struct
{
    int status;
    double look_angle_rad;
    double slant_range_ft;
    double target_x_ft;
    double target_y_ft;
    double start_height_ft;
} ZeroInitialData_t;

typedef struct
{
    double max_range_ft;
    double angle_at_max_rad;
} MaxRangeResult_t;

typedef struct Engine_s Engine_t;

typedef ErrorCode IntegrateFunc(
    Engine_t *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr);

typedef IntegrateFunc *IntegrateFuncPtr;

typedef struct Engine_s
{
    int integration_step_count;
    V3dT gravity_vector;
    Config_t config;
    ShotProps_t shot;
    IntegrateFuncPtr integrate_func_ptr;
    char err_msg[MAX_ERR_MSG_LEN];
} Engine_t;

// Cross-platform Engine_t_ERR macro
// This macro logs the error and saves it to the engine, then evaluates to the error code.
#define Engine_t_ERR(eng, code, format, ...) \
    Engine_t_log_and_save_error((eng), (code), __FILE__, __LINE__, __func__, format, ##__VA_ARGS__)

#ifdef __cplusplus
extern "C"
{
#endif
    ErrorCode Engine_t_log_and_save_error(
        Engine_t *eng,
        ErrorCode code,
        const char *file,
        int line,
        const char *func,
        const char *format,
        ...);

    void Engine_t_release_trajectory(Engine_t *eng);

    ErrorCode Engine_t_integrate(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr);

    ErrorCode Engine_t_find_apex(Engine_t *eng, BaseTrajData_t *apex);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_ENGINE_H
