#ifndef BCLIBC_TDF_H
#define BCLIBC_TDF_H

#include "v3d.h"
#include "bclib.h"

#define TDF_EPSILON 1e-6

// typedef struct {
//     BaseTrajData_t data;
//     TrajFlag_t flag;
// } TrajDataRow_t;

typedef struct
{
    ShotProps_t *props;
    TrajFlag_t filter;
    TrajFlag_t current_flag;
    TrajFlag_t seen_zero;
    double time_of_last_record;
    double time_step;
    double range_step;
    double range_limit;
    BaseTrajData_t *prev_data;
    BaseTrajData_t *prev_prev_data;
    double next_record_distance;
    double look_angle_rad;
    double look_angle_tangent;
    ErrorStack error_stack;
} TrajectoryDataFilter_t;

#ifdef __cplusplus
extern "C"
{
#endif

    void TrajectoryDataFilter_t_init(
        TrajectoryDataFilter_t *tdf,
        ShotProps_t *props,
        TrajFlag_t filter_flags,
        V3dT initial_position,
        V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad,
        double range_limit,
        double range_step,
        double time_step);

    // void TrajectoryDataFilter_t_record(
    //     TrajectoryDataFilter_t *tdf,
    //     const BaseTrajData_t *new_data);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_TDF_H