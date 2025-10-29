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
