#ifndef BCLIBC_TRAJ_FILTER_HPP
#define BCLIBC_TRAJ_FILTER_HPP

#include "bclibc_base_traj_seq.h"
#include <vector>

typedef struct
{
    BCLIBC_BaseTrajData data;
    BCLIBC_TrajFlag flag;
} BCLIBC_FlaggedData;

class BCLIBC_TrajectoryData
{
};

class BCLIBC_TrajectoryDataFilter
{
private:
    static constexpr double EPSILON = 1e-6;
    static constexpr double SEPARATE_ROW_TIME_DELTA = 1e-5;

private:
    std::vector<BCLIBC_TrajectoryData> records;
    const BCLIBC_ShotProps *props;
    BCLIBC_TrajFlag filter;
    BCLIBC_TrajFlag seen_zero;
    double time_of_last_record;
    double time_step;
    double range_step;
    double range_limit;
    BCLIBC_BaseTrajData prev_data;
    BCLIBC_BaseTrajData prev_prev_data;
    double next_record_distance;
    double look_angle_rad;
    double look_angle_tangent;

public:
    BCLIBC_TrajectoryDataFilter(
        const BCLIBC_ShotProps *props,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad,
        double range_limit,
        double range_step,
        double time_step);

    void record(BCLIBC_BaseTrajData *new_data);

private:
    void add_row(std::vector<BCLIBC_FlaggedData> *rows, BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag);
};

#endif // BCLIBC_TRAJ_FILTER_HPP