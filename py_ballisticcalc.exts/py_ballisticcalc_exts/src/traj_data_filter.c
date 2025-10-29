#include "traj_data_filter.h"
#include "base_traj_seq.h"

#define TDF_EPSILON 1e-6

void TrajectoryDataFilter_t_init(
    TrajectoryDataFilter_t *tdf,
    ShotProps_t *props,
    TrajFlag_t filter_flags,
    V3dT initial_position,
    V3dT initial_velocity,
    double barrel_angle_rad,
    double look_angle_rad,
    double range_limit,
    double range_step,
    double time_step)
{
    // tdf->records
    tdf->props = props;
    tdf->filter = filter_flags;
    tdf->seen_zero = TFLAG_NONE;
    tdf->time_step = time_step;
    tdf->range_step = range_step;
    tdf->range_limit = range_limit;
    tdf->time_of_last_record = 0.0;
    tdf->next_record_distance = 0.0;
    tdf->prev_data = NULL;
    tdf->prev_prev_data = NULL;
    tdf->look_angle_rad = look_angle_rad;
    tdf->look_angle_tangent = tan(look_angle_rad);
    if (tdf->filter & TFLAG_MACH)
    {
        double mach;
        double density;
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &tdf->props->atmo,
            initial_position.y,
            &density, &mach);
        if (mag(&initial_velocity) < mach)
        {
            // If we start below Mach 1, we won't look for Mach crossings
            tdf->filter &= ~TFLAG_MACH;
        }
    }
    if (tdf->filter * TFLAG_ZERO)
    {
        if (initial_position.y >= 0)
        {
            // If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
            tdf->filter &= ~TFLAG_ZERO_UP;
        }
        else if (initial_position.y < 0 && barrel_angle_rad <= tdf->look_angle_rad)
        {
            // If shot starts below zero and barrel points below line of sight we won't look for any crossings.
            tdf->filter &= ~(TFLAG_ZERO | TFLAG_MRT);
        }
    }
}

void TrajectoryDataFilter_t_record(
    TrajectoryDataFilter_t *tdf,
    const BaseTrajData_t *new_data)
{
// For each integration step, creates TrajectoryData records based on filter/step criteria.
rows:
    List[Tuple[BaseTrajData, Union[TrajFlag, int]]] = [];

    if (new_data->time == 0.0)
    {
        // Always record starting point
        TrajectoryDataFilter_t_add_row(
            &new_data,
            (tdf->range_step > 0 || tdf->time_step > 0) ? TFLAG_RANGE : TFLAG_NONE);
    }
    else
    {
        // region RANGE steps
        if (tdf->range_step > 0)
        {
            while (tdf->next_record_distance + tdf->range_step <= new_data->position.x)
            {
                new_row = NULL;
                record_distance = tdf->next_record_distance + tdf->range_step;
                if (record_distance > tdf->range_limit + TDF_EPSILON)
                {
                    tdf->range_step = -1; // Don't calculate range steps past range_limit
                    break;
                }
                if (fabs(record_distance - new_data->position.x) < TDF_EPSILON)
                {
                    new_row = new_data;
                }
                else if (tdf->prev_data && tdf->prev_prev_data)
                {
                    err = BaseTrajData_t_interpolate(
                        KEY_POS_X, record_distance,
                        tdf->prev_prev_data, tdf->prev_data,
                        new_data, &new_row);
                }
                if (new_row)
                {
                    tdf->next_record_distance += tdf->range_step;
                    TrajectoryDataFilter_t_add_row(&new_row, TFLAG_RANGE);
                }
                else
                {
                    break; // Can't interpolate without previous data
                }
            }
        }
        // endregion RANGE steps
        // region Time steps
        if (tdf->time_step > 0 && tdf->prev_data && tdf->prev_prev_data)
        {
            while (tdf->time_of_last_record + tdf->time_step <= new_data->time)
            {
                tdf->time_of_last_record += tdf->time_step;
                err = BaseTrajData_t_interpolate(
                    KEY_TIME,
                    tdf->time_of_last_record,
                    tdf->prev_prev_data, tdf->prev_data,
                    new_data, &new_row);
            }
        }
        // endregion Time steps
        if (
            tdf->filter & TFLAG_APEX && tdf->prev_data && tdf->prev_prev_data && tdf->prev_data->velocity.y > 0 && new_data->velocity.y <= 0)
        {
            // "Apex" is the point where the vertical component of velocity goes from positive to negative.
            err = BaseTrajData_t_interpolate(
                KEY_VEL_Y, 0.0,
                tdf->prev_prev_data,
                tdf->prev_data,
                new_data, &new_row);
            TrajectoryDataFilter_t_add_row(&new_row, TFLAG_APEX);
            tdf->filter &= ~TFLAG_APEX; // Don't look for more apices
        }
    }
    // tdf->records.extend([TrajectoryData.from_base_data(self.props, data, flag) for data, flag in rows])

    // region Points that must be interpolated on TrajectoryData instances
    if (tdf->prev_data && tdf->prev_prev_data)
    {
        compute_flags = TFLAG_NONE;
        if (
            tdf->filter & TFLAG_MACH && tdf->prev_data && mag(new_data->velocity) < new_data->mach)
        {
            compute_flags |= TFLAG_MACH;
            tdf->filter &= ~TFLAG_MACH; // Don't look for more Mach crossings
        }
        // region ZERO checks (done on TrajectoryData objects so we can interpolate for .slant_height)
    }
}

static inline void TrajectoryDataFilter_t_add_row(
    // TrajectoryDataFilter_t *tdf,
    const BaseTrajData_t *data,
    TrajFlag_t flag)
{
    // ssize_t idx = bisect_left(rows, data->time, key);
    // if (idx < rows)
    // {
    //     // If we match existing row's time then just add this flag to the row
    //     if (fabs(rows[idx][0].time - data->time) < SEPARATE_ROW_TIME_DELTA) {
    //         rows[idx] = (rows[idx][0], rows[idx][1] | flag);
    //         return;
    //     }
    //     if (idx > 0 && abs(rows[idx - 1][0].time - data->time) < SEPARATE_ROW_TIME_DELTA) {
    //         rows[idx - 1] = (rows[idx - 1][0], rows[idx - 1][1] | flag);
    //         return;
    //     }
    //     rows.insert(idx, (data, flag));
    // }
}
