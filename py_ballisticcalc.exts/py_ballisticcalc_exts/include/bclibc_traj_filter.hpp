#ifndef BCLIBC_TRAJ_FILTER_HPP
#define BCLIBC_TRAJ_FILTER_HPP

#include "bclibc_base_traj_seq.h"
#include "bclibc_interp.h"
#include <vector>

namespace bclibc
{

#define BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT 15

    BCLIBC_BaseTrajData BCLIBC_BaseTrajData_init(void);

    typedef enum
    {
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_TIME,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DISTANCE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_VELOCITY,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_MACH,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_HEIGHT,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_HEIGHT,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DROP_ANGLE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE_ANGLE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_DISTANCE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ANGLE,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DENSITY_RATIO,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DRAG,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ENERGY,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_OGW,
        BCLIBC_TRAJECTORY_DATA_INTERP_KEY_FLAG
    } BCLIBC_TrajectoryData_InterpKey;

    typedef struct
    {
        BCLIBC_BaseTrajData data;
        BCLIBC_TrajFlag flag;
    } BCLIBC_FlaggedData;

    struct BCLIBC_TrajectoryData
    {
    public:
        // data fields
        double time = 0.0;                            // Flight time in seconds
        double distance_ft = 0.0;                     // Down-range (x-axis) coordinate of this point
        double velocity_fps = 0.0;                    // Velocity
        double mach = 0.0;                            // Velocity in Mach terms
        double height_ft = 0.0;                       // Vertical (y-axis) coordinate of this point
        double slant_height_ft = 0.0;                 // Distance orthogonal to sight-line
        double drop_angle_rad = 0.0;                  // Slant_height in angular terms
        double windage_ft = 0.0;                      // Windage (z-axis) coordinate of this point
        double windage_angle_rad = 0.0;               // Windage in angular terms
        double slant_distance_ft = 0.0;               // Distance along sight line that is closest to this point
        double angle_rad = 0.0;                       // Angle of velocity vector relative to x-axis
        double density_ratio = 0.0;                   // Ratio of air density here to standard density
        double drag = 0.0;                            // Standard Drag Factor at this point
        double energy_ft_lb = 0.0;                    // Energy of bullet at this point
        double ogw_lb = 0.0;                          // Optimal game weight, given .energy
        BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE; // Row type

        // methods
        BCLIBC_TrajectoryData() = default;
        BCLIBC_TrajectoryData(const BCLIBC_TrajectoryData &) = default;
        BCLIBC_TrajectoryData &operator=(const BCLIBC_TrajectoryData &) = default;
        BCLIBC_TrajectoryData(BCLIBC_TrajectoryData &&) noexcept = default;
        BCLIBC_TrajectoryData &operator=(BCLIBC_TrajectoryData &&) noexcept = default;
        ~BCLIBC_TrajectoryData() = default;

        // BCLIBC_TrajectoryData(
        //     double time,              // Flight time in seconds
        //     double distance_ft,       // Down-range (x-axis) coordinate of this point
        //     double velocity_fps,      // Velocity
        //     double mach,              // Velocity in Mach terms
        //     double height_ft,         // Vertical (y-axis) coordinate of this point
        //     double slant_height_ft,   // Distance  # Distance orthogonal to sight-line
        //     double drop_angle_rad,    // Slant_height in angular terms
        //     double windage_ft,        // Windage (z-axis) coordinate of this point
        //     double windage_angle_rad, // Windage in angular terms
        //     double slant_distance_ft, // Distance along sight line that is closest to this point
        //     double angle_rad,         // Angle of velocity vector relative to x-axis
        //     double density_ratio,     // Ratio of air density here to standard density
        //     double drag,              // Standard Drag Factor at this point
        //     double energy_ft_lb,      // Energy of bullet at this point
        //     double ogw_lb,            // Optimal game weight, given .energy
        //     BCLIBC_TrajFlag flag      // Row type
        // );

        // BCLIBC_TrajectoryData();

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            double time,
            const BCLIBC_V3dT *range_vector,
            const BCLIBC_V3dT *velocity_vector,
            double mach,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            const BCLIBC_BaseTrajData *data,
            BCLIBC_TrajFlag flag = BCLIBC_TRAJ_FLAG_NONE);

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            const BCLIBC_FlaggedData *data);

        static BCLIBC_TrajectoryData interpolate(
            BCLIBC_TrajectoryData_InterpKey key,
            double value,
            const BCLIBC_TrajectoryData *t0,
            const BCLIBC_TrajectoryData *t1,
            const BCLIBC_TrajectoryData *t2,
            BCLIBC_TrajFlag flag,
            BCLIBC_InterpMethod method = BCLIBC_INTERP_METHOD_PCHIP);

        double get_key_val(int key) const;
        void set_key_val(int key, double value);
    };

    class BCLIBC_TrajectoryDataFilter
    {
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
        std::vector<BCLIBC_TrajectoryData> const &get_records() const;
        void append(const BCLIBC_TrajectoryData *new_data);
        void insert(const BCLIBC_TrajectoryData *new_data, size_t index);
        const BCLIBC_TrajectoryData &get_record(std::ptrdiff_t index) const;

    private:
        // constants
        static constexpr double EPSILON = 1e-6;
        static constexpr double SEPARATE_ROW_TIME_DELTA = 1e-5;

        // data fields
        std::vector<BCLIBC_TrajectoryData> records;
        const BCLIBC_ShotProps *props;
        BCLIBC_TrajFlag filter;
        double time_of_last_record;
        double time_step;
        double range_step;
        double range_limit;
        BCLIBC_BaseTrajData prev_data;
        BCLIBC_BaseTrajData prev_prev_data;
        double next_record_distance;
        double look_angle_rad;
        double look_angle_tangent;

        // internal helpers
        template <typename T, typename TimeAccessor>
        void merge_sorted_record(
            std::vector<T> &container,
            const T &new_record,
            TimeAccessor getTime);

        bool can_interpolate(const BCLIBC_BaseTrajData *new_data) const;
        void add_row(std::vector<BCLIBC_FlaggedData> *rows, BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag);
    };

};

#endif // BCLIBC_TRAJ_FILTER_HPP
