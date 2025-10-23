#ifndef ENGINE_H
#define ENGINE_H

#include "v3d.h"
#include "bclib.h"
#include "base_traj_seq.h"

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
    Engine_t *engine_ptr,
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
} Engine_t;

#ifdef __cplusplus
extern "C"
{
#endif

    void Engine_t_release_trajectory(Engine_t *engine_ptr);
    ErrorCode Engine_t_integrate(
        Engine_t *engine_ptr,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr);

    ErrorCode Engine_t_find_apex(Engine_t *engine_ptr, BaseTrajData_t *apex);

#ifdef __cplusplus
}
#endif

#endif // ENGINE_H
