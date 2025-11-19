#ifndef BCLIBC_TRAJ_FILTER_HPP
#define BCLIBC_TRAJ_FILTER_HPP

#include <vector>
#include "bclibc/traj_data.hpp"

namespace bclibc
{
    class BCLIBC_TrajectoryDataFilter : public BCLIBC_BaseTrajHandlerInterface
    {
    public:
        BCLIBC_TrajectoryDataFilter(
            std::vector<BCLIBC_TrajectoryData> *records,
            const BCLIBC_ShotProps *props,
            BCLIBC_TrajFlag filter_flags,
            double range_limit = 0.0,
            double range_step = 0.0,
            double time_step = 0.0);

    private:
        void init(const BCLIBC_BaseTrajData *data);

    public:
        BCLIBC_ErrorType handle(const BCLIBC_BaseTraj data) override;

        void record(const BCLIBC_BaseTrajData *new_data);
        std::vector<BCLIBC_TrajectoryData> const &get_records() const;
        void append(const BCLIBC_TrajectoryData *new_data);
        const BCLIBC_TrajectoryData &get_record(std::ptrdiff_t index) const;
        void finalize();

    private:
        // constants
        static constexpr double EPSILON = 1e-6;
        static constexpr double SEPARATE_ROW_TIME_DELTA = 1e-5;

        // data fields
        std::vector<BCLIBC_TrajectoryData> *records;
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
        void add_row(std::vector<BCLIBC_FlaggedData> *rows, const BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag);
    };

};

#endif // BCLIBC_TRAJ_FILTER_HPP
