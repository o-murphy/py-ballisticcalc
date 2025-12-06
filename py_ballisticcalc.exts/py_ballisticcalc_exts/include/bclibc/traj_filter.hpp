#ifndef BCLIBC_TRAJ_FILTER_HPP
#define BCLIBC_TRAJ_FILTER_HPP

#include <vector>
#include "bclibc/traj_data.hpp"
#include <functional>

namespace bclibc
{
    // ============================================================================
    // BCLIBC_TrajectoryDataFilter
    // ============================================================================

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
            BCLIBC_TerminationReason &termination_reason_ref,
            double range_limit = 0.0,
            double range_step = 0.0,
            double time_step = 0.0);

        /**
         * @brief Finalizes trajectory filtering.
         *
         * Ensures that the last trajectory point is recorded if needed.
         */
        ~BCLIBC_TrajectoryDataFilter();

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

        BCLIBC_TerminationReason &termination_reason_ref;

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

    // ============================================================================
    // BCLIBC_GenericTerminator
    // ============================================================================

    /**
     * @brief Generic termination handler with lambda condition.
     *
     * Replaces all specific terminators (MinVelocity, MaxDrop, etc.) with
     * a single configurable class.
     *
     * USAGE:
     *   BCLIBC_GenericTerminator term(reason, VELOCITY_REACHED,
     *       [min_v](const BCLIBC_BaseTrajData& d) {
     *           return d.velocity().mag() < min_v;
     *       });
     */
    class BCLIBC_GenericTerminator : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        BCLIBC_TerminationReason &termination_reason_ref;
        BCLIBC_TerminationReason reason_value;
        std::function<bool(const BCLIBC_BaseTrajData &)> condition;
        const char *debug_name;

    public:
        /**
         * @brief Constructs generic terminator with lambda condition.
         *
         * @param reason_ref Reference to reason variable
         * @param reason_value Value to set when condition triggers
         * @param condition Lambda that returns true when termination should occur
         * @param debug_name Optional name for debug logging
         */
        BCLIBC_GenericTerminator(
            BCLIBC_TerminationReason &reason_ref,
            BCLIBC_TerminationReason reason_value,
            std::function<bool(const BCLIBC_BaseTrajData &)> condition,
            const char *debug_name = "GenericTerminator");

        void handle(const BCLIBC_BaseTrajData &data) override;
    };

    // ============================================================================
    // BCLIBC_EssentialTerminators
    // ============================================================================

    /**
     * @brief A single handler that combines the main trajectory completion criteria:
     * Min Velocity, Max Drop, Min Altitude, and Range Limit.
     */
    class BCLIBC_EssentialTerminators : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        // constants
        static constexpr int MIN_ITERATIONS_COUNT = 3; // Always expects at least 3 iterations

        // Range Limit
        double range_limit_ft;
        int step_count;

        // Min Velocity
        double min_velocity_fps;

        // Max Drop
        double max_drop_ft;

        // Min Altitude
        double min_altitude_ft;
        double initial_altitude_ft;

        BCLIBC_TerminationReason &termination_reason_ref;

    public:
        BCLIBC_EssentialTerminators(
            const BCLIBC_ShotProps &shot,
            double range_limit_ft,
            double min_velocity_fps,
            double max_drop_ft,
            double min_altitude_ft,
            BCLIBC_TerminationReason &termination_reason_ref);

        void handle(const BCLIBC_BaseTrajData &data) override;
    };

    // ============================================================================
    // BCLIBC_SinglePointHandler
    // ============================================================================

    /**
     * @brief Handler that stores only the minimal data needed for single-point interpolation.
     *
     * Instead of storing all trajectory points, this handler keeps only a sliding window
     * of 3 points required for PCHIP interpolation. When the target is reached, it
     * interpolates immediately and discards older data.
     *
     * MEMORY: 3 * BCLIBC_BaseTrajData (~192 bytes) vs full trajectory (~N * 64 bytes)
     */
    class BCLIBC_SinglePointHandler : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        BCLIBC_BaseTrajData_InterpKey key_kind;
        double target_value;
        bool is_found;
        BCLIBC_BaseTrajData result;

        // Sliding window of last 3 points
        BCLIBC_BaseTrajData points[3];
        int count; // Number of points received (0-3)
        bool target_passed;

        // Early termination reason
        BCLIBC_TerminationReason *termination_reason_ptr;

    public:
        /**
         * @brief Constructs handler for single-point interpolation.
         * @param key_kind Type of key to search by (POS_X, VEL_Y, etc.)
         * @param target_value Target value to interpolate at
         * @param termination_reason_ptr Optional pointer to reason for early termination
         */
        BCLIBC_SinglePointHandler(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double target_value,
            BCLIBC_TerminationReason *termination_reason_ptr);

        void handle(const BCLIBC_BaseTrajData &data) override;

        /**
         * @brief Returns whether target point was found and interpolated.
         */
        bool found() const;

        /**
         * @brief Returns interpolated result.
         * @throws std::runtime_error if target not found yet.
         */
        const BCLIBC_BaseTrajData &get_result() const;

        const BCLIBC_BaseTrajData &get_last() const;

        /**
         * @brief Returns number of points processed.
         */
        int get_count() const;
    };

    // ============================================================================
    // BCLIBC_ZeroCrossingHandler
    // ============================================================================

    /**
     * @brief Handler that detects zero-crossing of slant height without storing full trajectory.
     *
     * Monitors trajectory points for sign change in slant height (py*cos - px*sin).
     * When crossing detected, performs linear interpolation to find exact crossing point.
     *
     * MEMORY: 2 * BCLIBC_BaseTrajData (~128 bytes) vs full trajectory
     */
    class BCLIBC_ZeroCrossingHandler : public BCLIBC_BaseTrajDataHandlerInterface
    {
    private:
        double look_angle_cos_;
        double look_angle_sin_;
        bool is_found;
        double result_slant_distance;

        BCLIBC_BaseTrajData prev_point;
        bool has_prev_;

        BCLIBC_TerminationReason *termination_reason_ptr;

    public:
        /**
         * @brief Constructs handler for zero-crossing detection.
         * @param look_angle_rad Look angle in radians (line of sight angle)
         * @param termination_reason_ptr Optional pointer to reason for early termination
         */
        explicit BCLIBC_ZeroCrossingHandler(
            double look_angle_rad, BCLIBC_TerminationReason *termination_reason_ptr);

        void handle(const BCLIBC_BaseTrajData &data) override;

        /**
         * @brief Returns whether zero-crossing was found.
         */
        bool found() const;

        /**
         * @brief Returns slant distance at zero-crossing.
         * @return Slant distance in feet, or 0.0 if not found.
         */
        double get_slant_distance() const;
    };
}; // namespace bclibc

#endif // BCLIBC_TRAJ_FILTER_HPP
