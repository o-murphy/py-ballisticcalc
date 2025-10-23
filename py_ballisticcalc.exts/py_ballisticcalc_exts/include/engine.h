#ifndef ENGINE_H
#define ENGINE_H

#include "v3d.h"
#include "bclib.h"
#include "base_traj_seq.h"

#include <stdarg.h> // for va_list, va_start, va_end, va_copy
#include <stdio.h>  // for fprintf
#include <string.h> // Потрібен для vsnprintf

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

typedef struct engine_t Engine_t;

typedef ErrorCode IntegrateFunc(
    Engine_t *eng,
    double range_limit_ft,
    double range_step_ft,
    double time_step,
    TrajFlag_t filter_flags,
    BaseTrajSeq_t *traj_seq_ptr);

typedef IntegrateFunc *IntegrateFuncPtr;

typedef struct engine_t
{
    int integration_step_count;
    V3dT gravity_vector;
    Config_t config;
    ShotProps_t shot;
    IntegrateFuncPtr integrate_func_ptr;
    char err_msg[MAX_ERR_MSG_LEN];
} Engine_t;

#define Engine_t_ERR(eng, code, format, ...)                         \
    ({                                                                      \
        ErrorCode _code = code;                                             \
        Engine_t *_eng = eng;                                 \
        C_LOG(LOG_LEVEL_ERROR, format, ##__VA_ARGS__);                      \
        if (_eng != NULL && _code != NO_ERROR)                       \
        {                                                                   \
            Engine_t_save_err_internal(_eng, format, ##__VA_ARGS__); \
        }                                                                   \
        _code;                                                              \
    })

#ifdef __cplusplus
extern "C"
{
#endif
    ErrorCode Engine_t_save_err_internal(Engine_t *eng, const char *format, ...);
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

#endif // ENGINE_H
