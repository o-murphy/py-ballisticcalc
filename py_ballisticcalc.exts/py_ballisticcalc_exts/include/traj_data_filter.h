#ifndef BCLIBC_TDF_H
#define BCLIBC_TDF_H

#include "v3d.h"
#include "bclib.h"

#define TDF_EPSILON 1e-6

// typedef struct {
//     BCLIBC_BaseTrajData data;
//     BCLIBC_TrajFlag flag;
// } TrajDataRow_t;

typedef struct
{
    ShotProps_t *props;
    BCLIBC_TrajFlag filter;
    BCLIBC_TrajFlag current_flag;
    BCLIBC_TrajFlag seen_zero;
    double time_of_last_record;
    double time_step;
    double range_step;
    double range_limit;
    BCLIBC_BaseTrajData *prev_data;
    BCLIBC_BaseTrajData *prev_prev_data;
    double next_record_distance;
    double look_angle_rad;
    double look_angle_tangent;
    BCLIBC_ErrorStack error_stack;
} TrajectoryDataFilter_t;

#ifdef __cplusplus
extern "C"
{
#endif

    void TrajectoryDataFilter_t_init(
        TrajectoryDataFilter_t *tdf,
        ShotProps_t *props,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad,
        double range_limit,
        double range_step,
        double time_step);

    // void TrajectoryDataFilter_t_record(
    //     TrajectoryDataFilter_t *tdf,
    //     const BCLIBC_BaseTrajData *new_data);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_TDF_H