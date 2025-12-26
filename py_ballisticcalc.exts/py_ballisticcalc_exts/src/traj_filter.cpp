#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <cstring>
#include "bclibc/traj_filter.hpp"
#include "bclibc/log.hpp"

namespace bclibc
{
    // ============================================================================
    // BCLIBC_TrajectoryDataFilter
    // ============================================================================

    /**
     * @brief Constructor for trajectory data filter.
     * @param records Reference to a vector where filtered trajectory data will be stored.
     * @param props Shot properties including initial conditions and atmosphere.
     * @param filter_flags Flags specifying which trajectory features to filter (apex, Mach crossings, etc.).
     * @param range_limit Maximum horizontal range to consider for filtering.
     * @param range_step Interval in horizontal distance for recording filtered points.
     * @param time_step Interval in simulation time for recording filtered points.
     */
    BCLIBC_TrajectoryDataFilter::BCLIBC_TrajectoryDataFilter(
        std::vector<BCLIBC_TrajectoryData> &records,
        const BCLIBC_ShotProps &props,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_TerminationReason &termination_reason_ref,
        double range_limit,
        double range_step,
        double time_step)
        : records(records),
          props(props),
          filter(filter_flags),
          time_of_last_record(0.0),
          time_step(time_step),
          range_step(range_step),
          range_limit(range_limit),
          prev_data(),
          prev_prev_data(),
          next_record_distance(0.0),
          look_angle_tangent(std::tan(props.look_angle)),
          termination_reason_ref(termination_reason_ref) {};

    /**
     * @brief Finalizes trajectory filtering.
     *
     * Ensures that the last trajectory point is recorded if needed.
     */
    BCLIBC_TrajectoryDataFilter::~BCLIBC_TrajectoryDataFilter()
    {
        if (this->termination_reason_ref != BCLIBC_TerminationReason::TARGET_RANGE_REACHED)
        {
            BCLIBC_DEBUG(
                "Trajectory Filter Finalization check: prev_data.time=%.6f",
                this->prev_data.time);
            if (this->prev_data.time > this->get_record(-1).time)
            {
                BCLIBC_TrajectoryData fin(this->props, this->prev_data);
                this->append(fin);
            }
        }
    };

    /**
     * @brief Initializes the filter state based on the first trajectory point.
     * @param data The initial trajectory data point.
     *
     * Adjusts filter flags depending on starting altitude, velocity, and barrel orientation.
     */
    void BCLIBC_TrajectoryDataFilter::init(const BCLIBC_BaseTrajData &data)
    {
        if (filter & BCLIBC_TRAJ_FLAG_MACH)
        {
            double mach;
            double density_ratio;
            this->props.atmo.update_density_factor_and_mach_for_altitude(
                data.py,
                density_ratio,
                mach);

            if (data.velocity().mag() < mach)
            {
                // If we start below Mach 1, we won't look for Mach crossings
                this->filter = (BCLIBC_TrajFlag)((int)this->filter & ~(int)BCLIBC_TRAJ_FLAG_MACH);
            }
        }

        if (filter & BCLIBC_TRAJ_FLAG_ZERO)
        {
            if (data.py >= 0)
            {
                // If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
            }
            else if (data.py < 0 && this->props.barrel_elevation <= this->props.look_angle)
            {
                // If shot starts below zero and barrel points below line of sight we won't look for any crossings.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~(BCLIBC_TRAJ_FLAG_ZERO | BCLIBC_TRAJ_FLAG_MRT));
            }
        }
    };

    /**
     * @brief Handles a new trajectory data point.
     * @param data The latest raw trajectory data.
     *
     * Delegates to `record()` for interpolation and filtering.
     */
    void BCLIBC_TrajectoryDataFilter::handle(const BCLIBC_BaseTrajData &data)
    {
        this->record(data);
    };

    /**
     * @brief Checks if interpolation between previous data points is possible.
     * @param new_data The current trajectory data point.
     * @return True if we have sufficient previous points to interpolate.
     */
    bool BCLIBC_TrajectoryDataFilter::can_interpolate(const BCLIBC_BaseTrajData &new_data) const
    {
        return (this->prev_prev_data.time >= 0.0) &&
               (this->prev_data.time >= 0.0) &&
               (this->prev_prev_data.time < this->prev_data.time) &&
               (this->prev_data.time < new_data.time);
    };

    /**
     * @brief Records a new trajectory point, interpolates missing points based on time or range,
     *        and applies feature-specific filters (apex, Mach, zero crossings).
     * @param new_data The latest trajectory point from simulation.
     */
    void BCLIBC_TrajectoryDataFilter::record(const BCLIBC_BaseTrajData &new_data)
    {
        std::vector<BCLIBC_FlaggedData> rows;
        bool is_can_interpolate = this->can_interpolate(new_data);

        if (new_data.time == 0.0)
        {
            // Init on first point handle
            this->init(new_data);
            // Always record starting point
            this->add_row(rows, new_data, (this->range_step > 0 || this->time_step) ? BCLIBC_TRAJ_FLAG_RANGE : BCLIBC_TRAJ_FLAG_NONE);
        }
        else
        {
            // region RANGE steps
            if (this->range_step > 0.0)
            {
                while (this->next_record_distance + this->range_step - this->EPSILON <= new_data.px)
                {
                    BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData();

                    bool found_data = false;
                    double record_distance = this->next_record_distance + this->range_step;
                    if (record_distance > this->range_limit + this->EPSILON)
                    {
                        this->range_step = -1;
                        break;
                    }
                    if (std::fabs(record_distance - new_data.px) < this->EPSILON)
                    {
                        result_data = new_data;
                        found_data = true;
                    }
                    else if (is_can_interpolate) /* if (this->prev_data && this->prev_prev_data) */
                    {
                        try
                        {
                            BCLIBC_BaseTrajData::interpolate(
                                BCLIBC_BaseTrajData_InterpKey::POS_X,
                                record_distance,
                                this->prev_prev_data,
                                this->prev_data,
                                new_data,
                                result_data);
                            found_data = true;
                        }
                        catch (const std::domain_error &e)
                        {
                        }
                    }
                    if (found_data)
                    {
                        this->next_record_distance += this->range_step;
                        this->add_row(rows, result_data, BCLIBC_TRAJ_FLAG_RANGE);
                        this->time_of_last_record = result_data.time;
                    }
                    else
                    {
                        // Can't interpolate without valid data/segment
                        break;
                    }
                }
            }
            // endregion RANGE steps
            // region Time steps
            if (is_can_interpolate && this->time_step > 0.0)
            {
                while (this->time_of_last_record + this->time_step - this->EPSILON <= new_data.time)
                {

                    this->time_of_last_record += this->time_step;

                    BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData();

                    try
                    {
                        BCLIBC_BaseTrajData::interpolate(
                            BCLIBC_BaseTrajData_InterpKey::TIME,
                            this->time_of_last_record,
                            this->prev_prev_data,
                            this->prev_data,
                            new_data,
                            result_data);
                        this->add_row(rows, result_data, BCLIBC_TRAJ_FLAG_RANGE);
                    }
                    catch (const std::domain_error &e)
                    {
                        // Can't interpolate without valid data/segment
                        break;
                    }
                }
            }
            // endregion Time steps
            if (
                is_can_interpolate &&
                this->filter & BCLIBC_TRAJ_FLAG_APEX &&
                this->prev_data.vy > 0 &&
                new_data.vy <= 0)
            {
                // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData();

                try
                {
                    BCLIBC_BaseTrajData::interpolate(
                        BCLIBC_BaseTrajData_InterpKey::VEL_Y,
                        0.0,
                        this->prev_prev_data,
                        this->prev_data,
                        new_data,
                        result_data);
                    // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                    this->add_row(rows, result_data, BCLIBC_TRAJ_FLAG_APEX);
                    this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_APEX);
                }
                catch (const std::domain_error &e)
                {
                }
            }
        }

        // Commit
        if (!rows.empty())
        {
            for (const auto &new_row : rows)
            {
                this->records.emplace_back(this->props, new_row);
            }
        }

        // region Points that must be interpolated on TrajectoryData instances
        if (is_can_interpolate)
        {
            BCLIBC_TrajFlag compute_flags = BCLIBC_TRAJ_FLAG_NONE;
            if (
                this->filter & BCLIBC_TRAJ_FLAG_MACH &&
                new_data.velocity().mag() < new_data.mach)
            {
                compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_MACH);
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_MACH); // Don't look for more Mach crossings
            }
            // region ZERO checks (done on TrajectoryData objects so we can interpolate for .slant_height)
            if (this->filter & BCLIBC_TRAJ_FLAG_ZERO)
            {
                // Zero reference line is the sight line defined by look_angle
                double reference_height = new_data.px * this->look_angle_tangent;
                // If we haven't seen ZERO_UP, we look for that first
                if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_UP)
                {
                    if (new_data.py >= reference_height)
                    {
                        compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_ZERO_UP);
                        this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
                    }
                }
                // We've crossed above sight line; now look for crossing back through it
                else if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_DOWN)
                {
                    if (new_data.py < reference_height)
                    {
                        compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_ZERO_DOWN);
                        this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_DOWN);
                    }
                }
            }
            // endregion ZERO checks
            if (compute_flags)
            {
                // Instantiate TrajectoryData and interpolate
                BCLIBC_TrajectoryData t0(this->props, new_data);
                BCLIBC_TrajectoryData t1(this->props, this->prev_data);
                BCLIBC_TrajectoryData t2(this->props, this->prev_prev_data);
                std::vector<BCLIBC_TrajectoryData> add_td;
                if (compute_flags & BCLIBC_TRAJ_FLAG_MACH)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TrajectoryData_InterpKey::MACH,
                            1.0,
                            t0, t1, t2,
                            BCLIBC_TRAJ_FLAG_MACH));
                }
                if (compute_flags & BCLIBC_TRAJ_FLAG_ZERO)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TrajectoryData_InterpKey::SLANT_HEIGHT,
                            0.0,
                            t0, t1, t2,
                            compute_flags));
                }
                // Add TrajectoryData, keeping `results` sorted by time.
                for (const auto &td : add_td)
                {
                    this->merge_sorted_record(
                        this->records,
                        td,
                        [](const BCLIBC_TrajectoryData &t)
                        { return t.time; });
                }
            }
        }

        // endregion
        this->prev_prev_data = this->prev_data;
        this->prev_data = new_data;
    };

    /**
     * @brief Returns the vector of filtered and processed trajectory data.
     * @return Const reference to stored trajectory records.
     */
    std::vector<BCLIBC_TrajectoryData> const &BCLIBC_TrajectoryDataFilter::get_records() const
    {
        return this->records;
    };

    /**
     * @brief Appends a new trajectory data point to the stored records.
     * @param new_data Trajectory data to append.
     */
    void BCLIBC_TrajectoryDataFilter::append(const BCLIBC_TrajectoryData &new_data)
    {
        this->records.push_back(new_data);
    };

    /**
     * @brief Retrieves a specific trajectory record by index.
     * @param index Positive or negative index (negative counts from end).
     * @return Reference to the requested trajectory data.
     * @throws std::out_of_range if index is invalid or records are empty.
     */
    const BCLIBC_TrajectoryData &BCLIBC_TrajectoryDataFilter::get_record(std::ptrdiff_t index) const
    {
        const size_t size = this->records.size();
        if (size == 0)
        {
            throw std::out_of_range("Cannot get record from empty trajectory data.");
        }
        const std::ptrdiff_t signed_size = static_cast<std::ptrdiff_t>(size);
        const std::ptrdiff_t effective_index = (index >= 0) ? index : signed_size + index;
        if (effective_index < 0 || effective_index >= signed_size)
        {
            throw std::out_of_range("Index is out of bounds.");
        }
        return this->records[static_cast<size_t>(effective_index)];
    };

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
    void BCLIBC_TrajectoryDataFilter::merge_sorted_record(
        std::vector<T> &container,
        const T &new_record,
        TimeAccessor getTime)
    {
        double new_time = getTime(new_record);

        auto it = std::lower_bound(
            container.begin(),
            container.end(),
            new_time,
            [&getTime](const T &record_data, double time_to_find)
            {
                return getTime(record_data) < time_to_find;
            });

        if (it != container.end() && std::fabs(getTime(*it) - new_time) < this->SEPARATE_ROW_TIME_DELTA)
        {
            it->flag = (BCLIBC_TrajFlag)(it->flag | new_record.flag);
            return;
        }

        if (it != container.begin())
        {
            auto prev_it = std::prev(it);

            if (std::fabs(getTime(*prev_it) - new_time) < this->SEPARATE_ROW_TIME_DELTA)
            {
                prev_it->flag = (BCLIBC_TrajFlag)(prev_it->flag | new_record.flag);
                return;
            }
        }

        container.insert(it, new_record);
    };

    /**
     * @brief Adds a new row of trajectory data with a specific flag to a container,
     *        maintaining sorted order by time.
     * @param rows Vector to add the row to.
     * @param data Trajectory data to add.
     * @param flag Trajectory feature flag.
     */
    void BCLIBC_TrajectoryDataFilter::add_row(std::vector<BCLIBC_FlaggedData> &rows, const BCLIBC_BaseTrajData &data, BCLIBC_TrajFlag flag)
    {
        BCLIBC_FlaggedData new_row = {data, flag};

        this->merge_sorted_record(
            rows,
            new_row,
            [](const BCLIBC_FlaggedData &f)
            { return f.data.time; });
    };

    // ============================================================================
    // BCLIBC_GenericTerminator
    // ============================================================================

    /**
     * @brief Constructs generic terminator with lambda condition.
     *
     * @param reason_ref Reference to reason variable
     * @param reason_value Value to set when condition triggers
     * @param condition Lambda that returns true when termination should occur
     * @param debug_name Optional name for debug logging
     */
    BCLIBC_GenericTerminator::BCLIBC_GenericTerminator(
        BCLIBC_TerminationReason &termination_reason_ref,
        BCLIBC_TerminationReason reason_value,
        std::function<bool(const BCLIBC_BaseTrajData &)> condition,
        const char *debug_name)
        : termination_reason_ref(termination_reason_ref),
          reason_value(reason_value),
          condition(condition),
          debug_name(debug_name) {};

    void BCLIBC_GenericTerminator::handle(const BCLIBC_BaseTrajData &data)
    {
        if (condition(data))
        {
            termination_reason_ref = reason_value;
            BCLIBC_DEBUG("%s triggered", debug_name);
        }
    };

    // ============================================================================
    // BCLIBC_EssentialTerminators
    // ============================================================================

    BCLIBC_EssentialTerminators::BCLIBC_EssentialTerminators(
        const BCLIBC_ShotProps &shot,
        double range_limit_ft,
        double min_velocity_fps,
        double max_drop_ft,
        double min_altitude_ft,
        BCLIBC_TerminationReason &termination_reason_ref)
        : range_limit_ft(range_limit_ft),
          step_count(0), // Always start from 0
          min_velocity_fps(min_velocity_fps),
          max_drop_ft(-std::fabs(max_drop_ft) + std::fmin(0.0, -shot.cant_cosine * shot.sight_height)),
          min_altitude_ft(min_altitude_ft),
          initial_altitude_ft(shot.alt0),
          termination_reason_ref(termination_reason_ref) {};

    void BCLIBC_EssentialTerminators::handle(const BCLIBC_BaseTrajData &data)
    {
        // 1. Early return
        if (this->termination_reason_ref != BCLIBC_TerminationReason::NO_TERMINATE)
        {
            return;
        }

        // 2. Range Limit
        this->step_count++;
        if (this->step_count >= this->MIN_ITERATIONS_COUNT && data.px > this->range_limit_ft)
        {
            this->termination_reason_ref = BCLIBC_TerminationReason::TARGET_RANGE_REACHED;
            BCLIBC_DEBUG("MaxRange limit reached: %.2f > %.2f",
                         data.px, this->range_limit_ft);
            return;
        }

        // 3. Min Velocity
        const double velocity = data.velocity().mag();
        if (velocity < this->min_velocity_fps)
        {
            this->termination_reason_ref = BCLIBC_TerminationReason::MINIMUM_VELOCITY_REACHED;
            BCLIBC_DEBUG("MinVelocity termination: v=%.2f < %.2f",
                         velocity, this->min_velocity_fps);
            return;
        }

        // 4. Max Drop
        if (data.py < this->max_drop_ft)
        {
            this->termination_reason_ref = BCLIBC_TerminationReason::MAXIMUM_DROP_REACHED;
            BCLIBC_DEBUG("MaxDrop termination: y=%.2f < %.2f",
                         data.py, this->max_drop_ft);
            return;
        }

        // 5. Min Altitude
        if (data.vy <= 0.0)
        {
            double current_altitude = this->initial_altitude_ft + data.py;
            if (current_altitude < this->min_altitude_ft)
            {
                this->termination_reason_ref = BCLIBC_TerminationReason::MINIMUM_ALTITUDE_REACHED;
                BCLIBC_DEBUG("MinAltitude termination: alt=%.2f < %.2f",
                             current_altitude, this->min_altitude_ft);
                return;
            }
        }
    };

    // ============================================================================
    // BCLIBC_SinglePointHandler
    // ============================================================================

    /**
     * @brief Constructs handler for single-point interpolation.
     * @param key_kind Type of key to search by (POS_X, VEL_Y, etc.)
     * @param target_value Target value to interpolate at
     * @param termination_reason_ptr Optional pointer to reason for early termination
     */
    BCLIBC_SinglePointHandler::BCLIBC_SinglePointHandler(
        BCLIBC_BaseTrajData_InterpKey key_kind,
        double target_value,
        BCLIBC_TerminationReason *termination_reason_ptr)
        : key_kind(key_kind),
          target_value(target_value),
          is_found(false),
          count(0),
          target_passed(false),
          termination_reason_ptr(termination_reason_ptr) {};

    void BCLIBC_SinglePointHandler::handle(const BCLIBC_BaseTrajData &data)
    {
        if (this->is_found)
            return; // Already found target

        // Shift window: [0] <- [1] <- [2] <- new
        if (this->count >= 3)
        {
            this->points[0] = this->points[1];
            this->points[1] = this->points[2];
            this->points[2] = data;
        }
        else
        {
            this->points[this->count] = data;
            this->count++;
        }

        // Check if we have enough points and crossed target
        if (this->count >= 3 && !this->target_passed)
        {
            double val_prev = this->points[1][this->key_kind];
            double val_curr = this->points[2][this->key_kind];

            // Check if target is between previous and current point
            bool crossed = (val_prev <= this->target_value && this->target_value <= val_curr) ||
                           (val_curr <= this->target_value && this->target_value <= val_prev);

            if (crossed)
            {
                this->target_passed = true;
                // Interpolate immediately
                try
                {
                    BCLIBC_BaseTrajData::interpolate(
                        this->key_kind,
                        this->target_value,
                        this->points[0],
                        this->points[1],
                        this->points[2],
                        this->result);
                    this->is_found = true;
                    if (termination_reason_ptr != nullptr)
                    {
                        *this->termination_reason_ptr = BCLIBC_TerminationReason::HANDLER_REQUESTED_STOP;
                        BCLIBC_INFO("BCLIBC_SinglePointHandler requested early termination");
                    }
                }
                catch (const std::domain_error &)
                {
                    // Degenerate segment, continue
                }
            }
        }
    };

    /**
     * @brief Returns whether target point was found and interpolated.
     */
    bool BCLIBC_SinglePointHandler::found() const { return this->is_found; };

    /**
     * @brief Returns interpolated result.
     * @throws std::runtime_error if target not found yet.
     */
    const BCLIBC_BaseTrajData &BCLIBC_SinglePointHandler::get_result() const
    {
        if (!this->is_found)
        {
            throw std::runtime_error("Target point not found during integration");
        }
        return this->result;
    };

    const BCLIBC_BaseTrajData &BCLIBC_SinglePointHandler::get_last() const
    {
        if (this->count == 0)
        {
            throw std::out_of_range("Cannot get last point: the handler is empty (count = 0).");
        }

        if (this->count >= 3)
        {
            return this->points[2];
        }
        else
        {
            return this->points[this->count - 1];
        }
    }

    /**
     * @brief Returns number of points processed.
     */
    int BCLIBC_SinglePointHandler::get_count() const { return this->count; };

    // ============================================================================
    // BCLIBC_ZeroCrossingHandler
    // ============================================================================

    /**
     * @brief Constructs handler for zero-crossing detection.
     * @param look_angle_rad Look angle in radians (line of sight angle)
     * @param termination_reason_ptr Optional pointer to reason for early termination
     */
    BCLIBC_ZeroCrossingHandler::BCLIBC_ZeroCrossingHandler(
        double look_angle_rad, BCLIBC_TerminationReason *termination_reason_ptr)
        : look_angle_cos_(std::cos(look_angle_rad)),
          look_angle_sin_(std::sin(look_angle_rad)),
          is_found(false),
          result_slant_distance(0.0),
          has_prev_(false),
          termination_reason_ptr(termination_reason_ptr) {};

    void BCLIBC_ZeroCrossingHandler::handle(const BCLIBC_BaseTrajData &data)
    {
        if (this->is_found)
            return; // Already found crossing

        if (!this->has_prev_)
        {
            this->prev_point = data;
            this->has_prev_ = true;
            return;
        }

        // Compute slant heights
        double h_prev = this->prev_point.py * this->look_angle_cos_ - this->prev_point.px * this->look_angle_sin_;
        double h_curr = data.py * this->look_angle_cos_ - data.px * this->look_angle_sin_;

        // Check for zero-down crossing (positive -> negative/zero)
        if (h_prev > 0.0 && h_curr <= 0.0)
        {
            // Linear interpolation to find exact crossing point
            double denom = h_prev - h_curr;
            double t;

            if (denom == 0.0)
            {
                t = 1.0; // Points have same height, use current
            }
            else
            {
                t = h_prev / denom;
                t = std::fmax(0.0, std::fmin(1.0, t)); // Clamp [0,1]
            }

            // Interpolate position
            double ix = this->prev_point.px + t * (data.px - this->prev_point.px);
            double iy = this->prev_point.py + t * (data.py - this->prev_point.py);

            // Compute slant distance
            this->result_slant_distance = ix * this->look_angle_cos_ + iy * this->look_angle_sin_;
            this->is_found = true;
            if (this->termination_reason_ptr != nullptr)
            {
                *this->termination_reason_ptr = BCLIBC_TerminationReason::HANDLER_REQUESTED_STOP;
                BCLIBC_INFO("BCLIBC_ZeroCrossingHandler requested early termination");
            }
        }

        this->prev_point = data;
    };

    /**
     * @brief Returns whether zero-crossing was found.
     */
    bool BCLIBC_ZeroCrossingHandler::found() const { return this->is_found; };

    /**
     * @brief Returns slant distance at zero-crossing.
     * @return Slant distance in feet, or 0.0 if not found.
     */
    double BCLIBC_ZeroCrossingHandler::get_slant_distance() const { return this->result_slant_distance; };

}; // namespace bclibc
