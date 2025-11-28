#ifndef BCLIBC_TRAJ_FILTER_HPP
#define BCLIBC_TRAJ_FILTER_HPP

#include <vector>
#include "bclibc/traj_data.hpp"

namespace bclibc
{
    /**
     * @class BCLIBC_TrajectoryDataFilter
     * @brief Filters and interpolates trajectory data points from raw simulation output.
     *
     * This class manages trajectory records and applies filters such as:
     * - Mach number crossings
     * - Apex detection (highest vertical point)
     * - Zero crossing (line of sight reference)
     * - Time- and range-based sampling
     *
     * It maintains previous data points to allow cubic or linear interpolation
     * between trajectory points when necessary.
     */
    class BCLIBC_TrajectoryDataFilter : public BCLIBC_BaseTrajDataHandlerInterface
    {
    public:
        /**
         * @brief Constructor for trajectory data filter.
         * @param records Reference to a vector where filtered trajectory data will be stored.
         * @param props Shot properties including initial conditions and atmosphere.
         * @param filter_flags Flags specifying which trajectory features to filter (apex, Mach crossings, etc.).
         * @param range_limit Maximum horizontal range to consider for filtering.
         * @param range_step Interval in horizontal distance for recording filtered points.
         * @param time_step Interval in simulation time for recording filtered points.
         */
        BCLIBC_TrajectoryDataFilter(
            std::vector<BCLIBC_TrajectoryData> &records,
            const BCLIBC_ShotProps &props,
            BCLIBC_TrajFlag filter_flags,
            double range_limit = 0.0,
            double range_step = 0.0,
            double time_step = 0.0);

    private:
        /**
         * @brief Initializes the filter state based on the first trajectory point.
         * @param data The initial trajectory data point.
         *
         * Adjusts filter flags depending on starting altitude, velocity, and barrel orientation.
         */
        void init(const BCLIBC_BaseTrajData &data);

    public:
        /**
         * @brief Handles a new trajectory data point.
         * @param data The latest raw trajectory data.
         *
         * Delegates to `record()` for interpolation and filtering.
         */
        void handle(const BCLIBC_BaseTrajData &data) override;

        /**
         * @brief Records a new trajectory point, interpolates missing points based on time or range,
         *        and applies feature-specific filters (apex, Mach, zero crossings).
         * @param new_data The latest trajectory point from simulation.
         */
        void record(const BCLIBC_BaseTrajData &new_data);

        /**
         * @brief Returns the vector of filtered and processed trajectory data.
         * @return Const reference to stored trajectory records.
         */
        std::vector<BCLIBC_TrajectoryData> const &get_records() const;

        /**
         * @brief Appends a new trajectory data point to the stored records.
         * @param new_data Trajectory data to append.
         */
        void append(const BCLIBC_TrajectoryData &new_data);

        /**
         * @brief Retrieves a specific trajectory record by index.
         * @param index Positive or negative index (negative counts from end).
         * @return Reference to the requested trajectory data.
         * @throws std::out_of_range if index is invalid or records are empty.
         */
        const BCLIBC_TrajectoryData &get_record(std::ptrdiff_t index) const;

        /**
         * @brief Finalizes trajectory filtering.
         *
         * Ensures that the last trajectory point is recorded if needed.
         */
        void finalize();

    private:
        // constants
        static constexpr double EPSILON = 1e-6;
        static constexpr double SEPARATE_ROW_TIME_DELTA = 1e-5;

        // data fields
        std::vector<BCLIBC_TrajectoryData> &records;
        const BCLIBC_ShotProps &props;
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

        /**
         * @brief Inserts a new record into a sorted container, merging with existing entries
         *        if the time difference is below `SEPARATE_ROW_TIME_DELTA`.
         * @tparam T Type of record (TrajectoryData or FlaggedData)
         * @tparam TimeAccessor Function to access time from record.
         * @param container The vector to insert into.
         * @param new_record The new record to insert.
         * @param getTime Function to access the record's timestamp.
         */
        template <typename T, typename TimeAccessor>
        void merge_sorted_record(
            std::vector<T> &container,
            const T &new_record,
            TimeAccessor getTime);

        /**
         * @brief Checks if interpolation between previous data points is possible.
         * @param new_data The current trajectory data point.
         * @return True if we have sufficient previous points to interpolate.
         */
        bool can_interpolate(const BCLIBC_BaseTrajData &new_data) const;

        /**
         * @brief Adds a new row of trajectory data with a specific flag to a container,
         *        maintaining sorted order by time.
         * @param rows Vector to add the row to.
         * @param data Trajectory data to add.
         * @param flag Trajectory feature flag.
         */
        void add_row(std::vector<BCLIBC_FlaggedData> &rows, const BCLIBC_BaseTrajData &data, BCLIBC_TrajFlag flag);
    };
}; // namespace bclibc

#endif // BCLIBC_TRAJ_FILTER_HPP
