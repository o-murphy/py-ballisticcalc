#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <cstring>
#include "bclibc/traj_filter.hpp"

namespace bclibc
{
    BCLIBC_TrajectoryDataFilter::BCLIBC_TrajectoryDataFilter(
        std::vector<BCLIBC_TrajectoryData> *records,
        const BCLIBC_ShotProps *props,
        BCLIBC_TrajFlag filter_flags,
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
          prev_data(prev_data),
          prev_prev_data(prev_prev_data),
          next_record_distance(0.0),
          look_angle_tangent(std::tan(props->look_angle)) {};

    void BCLIBC_TrajectoryDataFilter::init(const BCLIBC_BaseTrajData &data)
    {

        if (this->records == nullptr)
        {
            throw std::invalid_argument("Records pointer cannot be null during construction.");
        }

        if (this->props == nullptr)
        {
            throw std::invalid_argument("Shot props pointer cannot be null during construction.");
        }

        if (filter & BCLIBC_TRAJ_FLAG_MACH)
        {
            double mach;
            double density_ratio;
            this->props->atmo.update_density_factor_and_mach_for_altitude(
                data.position.y,
                &density_ratio,
                &mach);

            if (data.velocity.mag() < mach)
            {
                // If we start below Mach 1, we won't look for Mach crossings
                this->filter = (BCLIBC_TrajFlag)((int)this->filter & ~(int)BCLIBC_TRAJ_FLAG_MACH);
            }
        }

        if (filter & BCLIBC_TRAJ_FLAG_ZERO)
        {
            if (data.position.y >= 0)
            {
                // If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
            }
            else if (data.position.y < 0 && this->props->barrel_elevation <= this->props->look_angle)
            {
                // If shot starts below zero and barrel points below line of sight we won't look for any crossings.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~(BCLIBC_TRAJ_FLAG_ZERO | BCLIBC_TRAJ_FLAG_MRT));
            }
        }
    };

    void BCLIBC_TrajectoryDataFilter::finalize()
    {
        BCLIBC_DEBUG(
            "Trajectory Filter Finalization check: prev_data.time=%.6f",
            this->prev_data.time);
        if (this->prev_data.time > this->get_record(-1).time)
        {
            BCLIBC_TrajectoryData fin(this->props, &this->prev_data);
            this->append(fin);
        }
    };

    BCLIBC_ErrorType BCLIBC_TrajectoryDataFilter::handle(const BCLIBC_BaseTraj &data)
    {
        BCLIBC_BaseTrajData new_data = data.as_BaseTrajData();
        this->record(new_data);
        return BCLIBC_ErrorType::NO_ERROR;
    };

    bool BCLIBC_TrajectoryDataFilter::can_interpolate(const BCLIBC_BaseTrajData &new_data) const
    {
        return (this->prev_prev_data.time >= 0.0) &&
               (this->prev_data.time >= 0.0) &&
               (this->prev_prev_data.time < this->prev_data.time) &&
               (this->prev_data.time < new_data.time);
    };

    void BCLIBC_TrajectoryDataFilter::record(const BCLIBC_BaseTrajData &new_data)
    {
        if (this->records == nullptr)
        {
            throw std::runtime_error("Attempt to access records on a null pointer after construction.");
        }

        std::vector<BCLIBC_FlaggedData> rows;
        bool is_can_interpolate = this->can_interpolate(new_data);

        if (new_data.time == 0.0)
        {
            // Init on first point handle
            this->init(new_data);
            // Always record starting point
            this->add_row(&rows, new_data, (this->range_step > 0 || this->time_step) ? BCLIBC_TRAJ_FLAG_RANGE : BCLIBC_TRAJ_FLAG_NONE);
        }
        else
        {
            // region RANGE steps
            if (this->range_step > 0.0)
            {
                while (this->next_record_distance + this->range_step - this->EPSILON <= new_data.position.x)
                {
                    BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData();

                    bool found_data = false;
                    double record_distance = this->next_record_distance + this->range_step;
                    if (record_distance > this->range_limit + this->EPSILON)
                    {
                        this->range_step = -1;
                        break;
                    }
                    if (std::fabs(record_distance - new_data.position.x) < this->EPSILON)
                    {
                        result_data = new_data;
                        found_data = true;
                    }
                    else if (is_can_interpolate) /* if (this->prev_data && this->prev_prev_data) */
                    {
                        BCLIBC_ErrorType err = BCLIBC_BaseTrajData::interpolate(
                            BCLIBC_BaseTraj_InterpKey::POS_X,
                            record_distance,
                            &this->prev_prev_data,
                            &this->prev_data,
                            &new_data,
                            &result_data);
                        if (err == BCLIBC_ErrorType::NO_ERROR)
                        {
                            found_data = true;
                        }
                    }
                    if (found_data)
                    {
                        this->next_record_distance += this->range_step;
                        this->add_row(&rows, result_data, BCLIBC_TRAJ_FLAG_RANGE);
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

                    BCLIBC_ErrorType err = BCLIBC_BaseTrajData::interpolate(
                        BCLIBC_BaseTraj_InterpKey::TIME,
                        this->time_of_last_record,
                        &this->prev_prev_data,
                        &this->prev_data,
                        &new_data,
                        &result_data);

                    if (err == BCLIBC_ErrorType::NO_ERROR)
                    {
                        this->add_row(&rows, result_data, BCLIBC_TRAJ_FLAG_RANGE);
                    }
                    else
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
                this->prev_data.velocity.y > 0 &&
                new_data.velocity.y <= 0)
            {
                // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData();

                BCLIBC_ErrorType err = BCLIBC_BaseTrajData::interpolate(
                    BCLIBC_BaseTraj_InterpKey::VEL_Y,
                    0.0,
                    &this->prev_prev_data,
                    &this->prev_data,
                    &new_data,
                    &result_data);
                if (err == BCLIBC_ErrorType::NO_ERROR)
                {
                    // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                    this->add_row(&rows, result_data, BCLIBC_TRAJ_FLAG_APEX);
                    this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_APEX);
                }
                else
                {
                    // pass
                }
            }
        }

        // Commit
        if (!rows.empty())
        {
            for (const auto &new_row : rows)
            {
                this->records->emplace_back(this->props, &new_row);
            }
        }

        // region Points that must be interpolated on TrajectoryData instances
        if (is_can_interpolate)
        {
            BCLIBC_TrajFlag compute_flags = BCLIBC_TRAJ_FLAG_NONE;
            if (
                this->filter & BCLIBC_TRAJ_FLAG_MACH &&
                new_data.velocity.mag() < new_data.mach)
            {
                compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_MACH);
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_MACH); // Don't look for more Mach crossings
            }
            // region ZERO checks (done on TrajectoryData objects so we can interpolate for .slant_height)
            if (this->filter & BCLIBC_TRAJ_FLAG_ZERO)
            {
                // Zero reference line is the sight line defined by look_angle
                double reference_height = new_data.position.x * this->look_angle_tangent;
                // If we haven't seen ZERO_UP, we look for that first
                if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_UP)
                {
                    if (new_data.position.y >= reference_height)
                    {
                        compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_ZERO_UP);
                        this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
                    }
                }
                // We've crossed above sight line; now look for crossing back through it
                else if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_DOWN)
                {
                    if (new_data.position.y < reference_height)
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
                BCLIBC_TrajectoryData t0(this->props, &new_data);
                BCLIBC_TrajectoryData t1(this->props, &this->prev_data);
                BCLIBC_TrajectoryData t2(this->props, &this->prev_prev_data);
                std::vector<BCLIBC_TrajectoryData> add_td;
                if (compute_flags & BCLIBC_TRAJ_FLAG_MACH)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TrajectoryData_InterpKey::MACH,
                            1.0,
                            &t0, &t1, &t2,
                            BCLIBC_TRAJ_FLAG_MACH));
                }
                if (compute_flags & BCLIBC_TRAJ_FLAG_ZERO)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TrajectoryData_InterpKey::SLANT_HEIGHT,
                            0.0,
                            &t0, &t1, &t2,
                            compute_flags));
                }
                // Add TrajectoryData, keeping `results` sorted by time.
                for (const auto &td : add_td)
                {
                    this->merge_sorted_record(
                        *this->records,
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

    std::vector<BCLIBC_TrajectoryData> const &BCLIBC_TrajectoryDataFilter::get_records() const
    {
        if (this->records == nullptr)
        {
            throw std::runtime_error("Attempt to access records on a null pointer after construction.");
        }
        return *this->records;
    };

    void BCLIBC_TrajectoryDataFilter::append(const BCLIBC_TrajectoryData &new_data)
    {
        if (this->records == nullptr)
        {
            throw std::runtime_error("Attempt to access records on a null pointer after construction.");
        }

        this->records->push_back(new_data);
    };

    const BCLIBC_TrajectoryData &BCLIBC_TrajectoryDataFilter::get_record(std::ptrdiff_t index) const
    {
        if (this->records == nullptr)
        {
            throw std::runtime_error("Attempt to access records on a null pointer after construction.");
        }

        const size_t size_t_size = this->records->size();
        const std::ptrdiff_t signed_size = (std::ptrdiff_t)size_t_size;
        std::ptrdiff_t signed_effective_index;
        if (signed_size == 0)
        {
            throw std::out_of_range("Cannot get record from empty trajectory data.");
        }
        if (index >= 0)
        {
            signed_effective_index = index;
        }
        else
        {
            signed_effective_index = signed_size + index;
        }
        if (signed_effective_index < 0 || signed_effective_index >= signed_size)
        {
            throw std::out_of_range("Index is out of bounds.");
        }
        return this->records->at((size_t)signed_effective_index);
    };

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

    void BCLIBC_TrajectoryDataFilter::add_row(std::vector<BCLIBC_FlaggedData> *rows, const BCLIBC_BaseTrajData &data, BCLIBC_TrajFlag flag)
    {
        BCLIBC_FlaggedData new_row = {data, flag};

        this->merge_sorted_record(
            *rows,
            new_row,
            [](const BCLIBC_FlaggedData &f)
            { return f.data.time; });
    };

};
