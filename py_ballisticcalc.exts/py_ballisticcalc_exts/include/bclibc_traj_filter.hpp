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
public:
    double time;              // Flight time in seconds
    double distance_ft;       // Down-range (x-axis) coordinate of this point
    double velocity_fps;      // Velocity
    double mach;              // Velocity in Mach terms
    double height_ft;         // Vertical (y-axis) coordinate of this point
    double slant_height_ft;   // Distance  # Distance orthogonal to sight-line
    double drop_angle_rad;    // Slant_height in angular terms
    double windage_ft;        // Windage (z-axis) coordinate of this point
    double windage_angle_rad; // Windage in angular terms
    double slant_distance_ft; // Distance along sight line that is closest to this point
    double angle_rad;         // Angle of velocity vector relative to x-axis
    double density_ratio;     // Ratio of air density here to standard density
    double drag;              // Standard Drag Factor at this point
    double energy_ft_lb;      // Energy of bullet at this point
    double ogw_lb;            // Optimal game weight, given .energy
    BCLIBC_TrajFlag flag;     // Row type

    BCLIBC_TrajectoryData(
        double time,              // Flight time in seconds
        double distance_ft,       // Down-range (x-axis) coordinate of this point
        double velocity_fps,      // Velocity
        double mach,              // Velocity in Mach terms
        double height_ft,         // Vertical (y-axis) coordinate of this point
        double slant_height_ft,   // Distance  # Distance orthogonal to sight-line
        double drop_angle_rad,    // Slant_height in angular terms
        double windage_ft,        // Windage (z-axis) coordinate of this point
        double windage_angle_rad, // Windage in angular terms
        double slant_distance_ft, // Distance along sight line that is closest to this point
        double angle_rad,         // Angle of velocity vector relative to x-axis
        double density_ratio,     // Ratio of air density here to standard density
        double drag,              // Standard Drag Factor at this point
        double energy_ft_lb,      // Energy of bullet at this point
        double ogw_lb,            // Optimal game weight, given .energy
        BCLIBC_TrajFlag flag      // Row type
    );

    BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_FlaggedData *data);

    BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_BaseTrajData *data,
        BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

    // BCLIBC_TrajectoryData(
    //     const BCLIBC_ShotProps *props,
    //     double time,
    //     BCLIBC_V3dT *range_vector,
    //     BCLIBC_V3dT *velocity_vector,
    //     double mach,
    //     BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

    static BCLIBC_TrajectoryData interpolate(
        BCLIBC_InterpKey key, 
        double value, 
        const BCLIBC_TrajectoryData *t0,
        const BCLIBC_TrajectoryData *t1,
        const BCLIBC_TrajectoryData *t2,
        BCLIBC_TrajFlag flag
    );
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
        double look_angle_rad = 0.0,
        double range_limit = 0.0,
        double range_step = 0.0,
        double time_step = 0.0);

    void record(BCLIBC_BaseTrajData *new_data);

private:
    bool can_interpolate(const BCLIBC_BaseTrajData *new_data) const;
    void add_row(std::vector<BCLIBC_FlaggedData> *rows, BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag);
};

#endif // BCLIBC_TRAJ_FILTER_HPP