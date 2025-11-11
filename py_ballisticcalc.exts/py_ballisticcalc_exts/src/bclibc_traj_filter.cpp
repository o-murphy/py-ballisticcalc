#include <cmath>
#include <algorithm>
#include <vector>
#include <stdexcept>
#include "bclibc_base_traj_seq.h"
#include "bclibc_traj_filter.hpp"
#include <cstring>

namespace bclibc
{

    // BCLIBC_TrajectoryData::BCLIBC_TrajectoryData() {};

    // guarantee complete C struct initialisation BCLIBC_BaseTrajData
    BCLIBC_BaseTrajData BCLIBC_BaseTrajData_init(void)
    {
        BCLIBC_BaseTrajData data; // = {} possibly can not work on MSVC, use memset
        std::memset(&data, 0, sizeof(data));
        data.time = -1.0;
        data.mach = -1.0;
        return data;
    };

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        double time,
        const BCLIBC_V3dT *range_vector,
        const BCLIBC_V3dT *velocity_vector,
        double mach_arg,
        BCLIBC_TrajFlag flag)
        : time(time), flag(flag)
    {
        // BCLIBC_Coriolis const *c = &props->coriolis;
        // fprintf(stderr,
        //     "%.10f %.10f %.10f %.10f %.10f %.10f %.10f %.10f %d %.10f\n",
        //     c->sin_lat,
        //     c->cos_lat,
        //     c->sin_az,
        //     c->cos_az,
        //     c->range_east,
        //     c->range_north,
        //     c->cross_east,
        //     c->cross_north,
        //     c->flat_fire_only,
        //     c->muzzle_velocity_fps
        // );
        BCLIBC_V3dT adjusted_range = BCLIBC_adjustRangeFromCoriolis(&props->coriolis, time, range_vector);
        // BCLIBC_V3dT adjusted_range = *range_vector;
        double spin_drift = BCLIBC_ShotProps_spinDrift(props, time);
        double velocity = BCLIBC_V3dT_mag(velocity_vector);

        // if (velocity < -1e6 || velocity > 1e6 || spin_drift < -1e6 || spin_drift > 1e6) {
        //     fprintf(stdout, "MEMERR: adjusted_range.z=%.6f, spin_drift=%.6f", adjusted_range.z, spin_drift);
        // }

        this->windage_ft = adjusted_range.z + spin_drift;

        // fprintf(stderr,
        //         "DEBUG_WINDAGE: time=%.6f, InputZ=%.6f, AdjustedZ=%.6f, SpinDrift=%.6f\n",
        //         time, range_vector->z, adjusted_range.z, spin_drift);

        double density_ratio_out, mach_out;
        BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
            &props->atmo, range_vector->y, &density_ratio_out, &mach_out);

        double trajectory_angle = std::atan2(velocity_vector->y, velocity_vector->x);
        double look_angle_cos = std::cos(props->look_angle);
        double look_angle_sin = std::sin(props->look_angle);

        this->distance_ft = adjusted_range.x;
        this->velocity_fps = velocity;

        this->mach = velocity / (mach_arg != 0.0 ? mach_arg : mach_out);

        this->height_ft = adjusted_range.y;
        this->slant_height_ft = adjusted_range.y * look_angle_cos - adjusted_range.x * look_angle_sin;
        this->drop_angle_rad = BCLIBC_getCorrection(adjusted_range.x, adjusted_range.y) -
                               (adjusted_range.x ? props->look_angle : 0.0);
        this->windage_angle_rad = BCLIBC_getCorrection(adjusted_range.x, this->windage_ft);
        this->slant_distance_ft = adjusted_range.x * look_angle_cos + adjusted_range.y * look_angle_sin;
        this->angle_rad = trajectory_angle;
        this->density_ratio = density_ratio_out;
        this->drag = BCLIBC_ShotProps_dragByMach(props, this->mach);
        this->energy_ft_lb = BCLIBC_calculateEnergy(props->weight, velocity);
        this->ogw_lb = BCLIBC_calculateOgw(props->weight, velocity);
    };

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_BaseTrajData *data,
        BCLIBC_TrajFlag flag)
        : BCLIBC_TrajectoryData(props, data->time, &data->position, &data->velocity, data->mach, flag) {};

    BCLIBC_TrajectoryData::BCLIBC_TrajectoryData(
        const BCLIBC_ShotProps *props,
        const BCLIBC_FlaggedData *data)
        : BCLIBC_TrajectoryData(props, &data->data, data->flag) {};

    BCLIBC_TrajectoryData BCLIBC_TrajectoryData::interpolate(
        BCLIBC_TrajectoryData_InterpKey key,
        double value,
        const BCLIBC_TrajectoryData *p0,
        const BCLIBC_TrajectoryData *p1,
        const BCLIBC_TrajectoryData *p2,
        BCLIBC_TrajFlag flag,
        BCLIBC_InterpMethod method)
    {
        if (p0 == nullptr || p1 == nullptr || p2 == nullptr)
        {
            throw std::invalid_argument("Interpolation points (p0, p1, p2) cannot be NULL.");
        }

        // The independent variable for interpolation (x-axis)
        double x_val = value;
        double x0 = p0->get_key_val((BCLIBC_TrajectoryData_InterpKey)key);
        double x1 = p1->get_key_val((BCLIBC_TrajectoryData_InterpKey)key);
        double x2 = p2->get_key_val((BCLIBC_TrajectoryData_InterpKey)key);

        // Use reflection to build the new TrajectoryData object

        // // Better copy data from p0 to fill uninterpolated or derived fields
        // BCLIBC_TrajectoryData interpolated_data;  // = {} possibly can not work on MSVC, use memset;
        BCLIBC_TrajectoryData interpolated_data = *p0;

        if (key < 0 || key > BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT)
        {
            throw std::runtime_error("Can't interpolate by unsupported key");
        }

        for (int field_key = 0; field_key < BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ACTIVE_COUNT; field_key++)
        {
            double y0 = p0->get_key_val((BCLIBC_TrajectoryData_InterpKey)field_key);
            double y1 = p1->get_key_val((BCLIBC_TrajectoryData_InterpKey)field_key);
            double y2 = p2->get_key_val((BCLIBC_TrajectoryData_InterpKey)field_key);

            double interpolated_value = 0.0;
            BCLIBC_ErrorType err = BCLIBC_E_NO_ERROR;

            if (field_key == key)
            {
                interpolated_value = x_val;
            }
            else
            {
                if (method == BCLIBC_INTERP_METHOD_PCHIP)
                {
                    interpolated_value = BCLIBC_interpolate3pt(
                        x_val, x0, x1, x2, y0, y1, y2);
                }
                else if (method == BCLIBC_INTERP_METHOD_LINEAR)
                {
                    if (x_val <= x1)
                    {
                        err = (BCLIBC_ErrorType)BCLIBC_interpolate2pt(x_val, x0, y0, x1, y1, &interpolated_value);
                    }
                    else
                    {
                        err = (BCLIBC_ErrorType)BCLIBC_interpolate2pt(x_val, x1, y1, x2, y2, &interpolated_value);
                    }
                    if (err != BCLIBC_E_NO_ERROR)
                    {
                        throw std::domain_error("Zero division error");
                    }
                }
                else
                {
                    throw std::invalid_argument("Invalid interpolation method provided.");
                }
            }

            interpolated_data.set_key_val(field_key, interpolated_value);
        }
        interpolated_data.flag = flag;
        return interpolated_data;
    };

    double BCLIBC_TrajectoryData::get_key_val(int key) const
    {
        switch ((BCLIBC_TrajectoryData_InterpKey)key)
        {
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_TIME:
            return this->time;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DISTANCE:
            return this->distance_ft;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_VELOCITY:
            return this->velocity_fps;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_MACH:
            return this->mach;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_HEIGHT:
            return this->height_ft;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_HEIGHT:
            return this->slant_height_ft;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DROP_ANGLE:
            return this->drop_angle_rad;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE:
            return this->windage_ft;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE_ANGLE:
            return this->windage_angle_rad;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_DISTANCE:
            return this->slant_distance_ft;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ANGLE:
            return this->angle_rad;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DENSITY_RATIO:
            return this->density_ratio;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DRAG:
            return this->drag;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ENERGY:
            return this->energy_ft_lb;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_OGW:
            return this->ogw_lb;
        default:
            return 0.0; // Error or unexpected key
        }
    };

    void BCLIBC_TrajectoryData::set_key_val(int key, double value)
    {
        switch ((BCLIBC_TrajectoryData_InterpKey)key)
        {
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_TIME:
            this->time = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DISTANCE:
            this->distance_ft = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_VELOCITY:
            this->velocity_fps = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_MACH:
            this->mach = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_HEIGHT:
            this->height_ft = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_HEIGHT:
            this->slant_height_ft = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DROP_ANGLE:
            this->drop_angle_rad = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE:
            this->windage_ft = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_WINDAGE_ANGLE:
            this->windage_angle_rad = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_DISTANCE:
            this->slant_distance_ft = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ANGLE:
            this->angle_rad = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DENSITY_RATIO:
            this->density_ratio = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_DRAG:
            this->drag = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_ENERGY:
            this->energy_ft_lb = value;
            break;
        case BCLIBC_TRAJECTORY_DATA_INTERP_KEY_OGW:
            this->ogw_lb = value;
            break;
            // No default needed
        }
    };

    BCLIBC_TrajectoryDataFilter::BCLIBC_TrajectoryDataFilter(
        const BCLIBC_ShotProps *props,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad,
        double range_limit,
        double range_step,
        double time_step)
        : props(props),
          filter(filter_flags),
          time_of_last_record(0.0),
          time_step(time_step),
          range_step(range_step),
          range_limit(range_limit),
          prev_data{BCLIBC_BaseTrajData_init()},
          prev_prev_data{BCLIBC_BaseTrajData_init()},
          next_record_distance(0.0),
          look_angle_rad(look_angle_rad),
          look_angle_tangent(std::tan(look_angle_rad))
    {

        if (filter & BCLIBC_TRAJ_FLAG_MACH)
        {
            double mach;
            double density_ratio;
            BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
                &props->atmo,
                initial_position.y,
                &density_ratio,
                &mach);

            if (BCLIBC_V3dT_mag(&initial_velocity) < mach)
            {
                // If we start below Mach 1, we won't look for Mach crossings
                this->filter = (BCLIBC_TrajFlag)((int)this->filter & ~(int)BCLIBC_TRAJ_FLAG_MACH);
            }
        }

        if (filter & BCLIBC_TRAJ_FLAG_ZERO)
        {
            if (initial_position.y >= 0)
            {
                // If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
            }
            else if (initial_position.y < 0 && barrel_angle_rad <= look_angle_rad)
            {
                // If shot starts below zero and barrel points below line of sight we won't look for any crossings.
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~(BCLIBC_TRAJ_FLAG_ZERO | BCLIBC_TRAJ_FLAG_MRT));
            }
        }
    };

    bool BCLIBC_TrajectoryDataFilter::can_interpolate(const BCLIBC_BaseTrajData *new_data) const
    {
        return (this->prev_prev_data.time >= 0.0) &&
               (this->prev_data.time >= 0.0) &&
               (this->prev_prev_data.time < this->prev_data.time) &&
               (this->prev_data.time < new_data->time);
    };

    void BCLIBC_TrajectoryDataFilter::record(BCLIBC_BaseTrajData *new_data)
    {
        if (new_data == nullptr)
        {
            return;
        };

        std::vector<BCLIBC_FlaggedData> rows;
        bool is_can_interpolate = this->can_interpolate(new_data);

        if (new_data->time == 0.0)
        {
            // Always record starting point
            this->add_row(&rows, new_data, (this->range_step > 0 || this->time_step) ? BCLIBC_TRAJ_FLAG_RANGE : BCLIBC_TRAJ_FLAG_NONE);
        }
        else
        {
            // region RANGE steps
            if (this->range_step > 0.0)
            {
                while (this->next_record_distance + this->range_step - this->EPSILON <= new_data->position.x)
                {
                    BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData_init();

                    bool found_data = false;
                    double record_distance = this->next_record_distance + this->range_step;
                    if (record_distance > this->range_limit + this->EPSILON)
                    {
                        this->range_step = -1;
                        break;
                    }
                    if (std::fabs(record_distance - new_data->position.x) < this->EPSILON)
                    {
                        result_data = *new_data;
                        found_data = true;
                    }
                    else if (is_can_interpolate) /* if (this->prev_data && this->prev_prev_data) */
                    {
                        BCLIBC_ErrorType err = BCLIBC_BaseTrajData_interpolate(
                            BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X,
                            record_distance,
                            &this->prev_prev_data,
                            &this->prev_data,
                            new_data,
                            &result_data);
                        if (err == BCLIBC_E_NO_ERROR)
                        {
                            found_data = true;
                        }
                    }
                    if (found_data)
                    {
                        this->next_record_distance += this->range_step;
                        this->add_row(&rows, &result_data, BCLIBC_TRAJ_FLAG_RANGE);
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
                while (this->time_of_last_record + this->time_step - this->EPSILON <= new_data->time)
                {

                    this->time_of_last_record += this->time_step;

                    BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData_init();

                    BCLIBC_ErrorType err = BCLIBC_BaseTrajData_interpolate(
                        BCLIBC_BASE_TRAJ_INTERP_KEY_TIME,
                        this->time_of_last_record,
                        &this->prev_prev_data,
                        &this->prev_data,
                        new_data,
                        &result_data);

                    if (err == BCLIBC_E_NO_ERROR)
                    {
                        this->add_row(&rows, &result_data, BCLIBC_TRAJ_FLAG_RANGE);
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
                new_data->velocity.y <= 0)
            {
                // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                BCLIBC_BaseTrajData result_data = BCLIBC_BaseTrajData_init();

                BCLIBC_ErrorType err = BCLIBC_BaseTrajData_interpolate(
                    BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y,
                    0.0,
                    &this->prev_prev_data,
                    &this->prev_data,
                    new_data,
                    &result_data);
                if (err == BCLIBC_E_NO_ERROR)
                {
                    // "Apex" is the point where the vertical component of velocity goes from positive to negative.
                    this->add_row(&rows, &result_data, BCLIBC_TRAJ_FLAG_APEX);
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
                this->records.emplace_back(this->props, &new_row);
            }
        }

        // region Points that must be interpolated on TrajectoryData instances
        if (is_can_interpolate)
        {
            BCLIBC_TrajFlag compute_flags = BCLIBC_TRAJ_FLAG_NONE;
            if (
                this->filter & BCLIBC_TRAJ_FLAG_MACH &&
                BCLIBC_V3dT_mag(&new_data->velocity) < new_data->mach)
            {
                compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_MACH);
                this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_MACH); // Don't look for more Mach crossings
            }
            // region ZERO checks (done on TrajectoryData objects so we can interpolate for .slant_height)
            if (this->filter & BCLIBC_TRAJ_FLAG_ZERO)
            {
                // Zero reference line is the sight line defined by look_angle
                double reference_height = new_data->position.x * this->look_angle_tangent;
                // If we haven't seen ZERO_UP, we look for that first
                if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_UP)
                {
                    if (new_data->position.y >= reference_height)
                    {
                        compute_flags = (BCLIBC_TrajFlag)(compute_flags | BCLIBC_TRAJ_FLAG_ZERO_UP);
                        this->filter = (BCLIBC_TrajFlag)(this->filter & ~BCLIBC_TRAJ_FLAG_ZERO_UP);
                    }
                }
                // We've crossed above sight line; now look for crossing back through it
                else if (this->filter & BCLIBC_TRAJ_FLAG_ZERO_DOWN)
                {
                    if (new_data->position.y < reference_height)
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
                BCLIBC_TrajectoryData t1(this->props, &this->prev_data);
                BCLIBC_TrajectoryData t2(this->props, &this->prev_prev_data);
                std::vector<BCLIBC_TrajectoryData> add_td;
                if (compute_flags & BCLIBC_TRAJ_FLAG_MACH)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TRAJECTORY_DATA_INTERP_KEY_MACH,
                            1.0,
                            &t0, &t1, &t2,
                            BCLIBC_TRAJ_FLAG_MACH));
                }
                if (compute_flags & BCLIBC_TRAJ_FLAG_ZERO)
                {
                    add_td.push_back(
                        BCLIBC_TrajectoryData::interpolate(
                            BCLIBC_TRAJECTORY_DATA_INTERP_KEY_SLANT_HEIGHT,
                            0.0,
                            &t0, &t1, &t2,
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
        this->prev_data = *new_data;
    };

    std::vector<BCLIBC_TrajectoryData> const &BCLIBC_TrajectoryDataFilter::get_records() const
    {
        return this->records;
    };

    void BCLIBC_TrajectoryDataFilter::append(const BCLIBC_TrajectoryData *new_data)
    {
        if (new_data == nullptr)
        {
            return;
        }

        this->records.push_back(*new_data);
    };

    void BCLIBC_TrajectoryDataFilter::insert(const BCLIBC_TrajectoryData *new_data, size_t index)
    {
        if (new_data == nullptr)
        {
            return;
        }

        if (index > this->records.size())
        {
            index = this->records.size();
        }

        auto position_iterator = this->records.begin() + index;

        this->records.insert(position_iterator, *new_data);
    };

    const BCLIBC_TrajectoryData &BCLIBC_TrajectoryDataFilter::get_record(std::ptrdiff_t index) const
    {
        const size_t size_t_size = this->records.size();
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
        return this->records.at((size_t)signed_effective_index);
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

    void BCLIBC_TrajectoryDataFilter::add_row(std::vector<BCLIBC_FlaggedData> *rows, BCLIBC_BaseTrajData *data, BCLIBC_TrajFlag flag)
    {
        if (rows == nullptr || data == nullptr)
        {
            return;
        }

        BCLIBC_FlaggedData new_row = {*data, flag};

        this->merge_sorted_record(
            *rows,
            new_row,
            [](const BCLIBC_FlaggedData &f)
            { return f.data.time; });
    };

};
