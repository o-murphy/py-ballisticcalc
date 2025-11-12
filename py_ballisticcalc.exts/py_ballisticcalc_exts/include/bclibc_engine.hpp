#ifndef BCLIBC_ENGINE_HPP
#define BCLIBC_ENGINE_HPP

#include "bclibc_engine.h"
#include "bclibc_traj_filter.hpp"

/*
Possible call chains:

BCLIBC_EngineT_findZeroAngle
 ├─> BCLIBC_EngineT_initZeroCalculation
 │    └─> BCLIBC_EngineT_findApex
 │         └─> BCLIBC_EngineT_integrate
 │              └─> eng->integrate_func_ptr
 ├─> BCLIBC_EngineT_findMaxRange
 │    ├─> BCLIBC_EngineT_findApex
 │    │    └─> BCLIBC_EngineT_integrate
 │    │         └─> eng->integrate_func_ptr
 │    └─> BCLIBC_EngineT_rangeForAngle
 │         └─> BCLIBC_EngineT_integrate
 │              └─> eng->integrate_func_ptr
 └─> BCLIBC_EngineT_errorAtDistance
      └─> BCLIBC_EngineT_integrate
      └─> BCLIBC_BaseTrajSeq_getAt / get_raw_item

BCLIBC_EngineT_zeroAngle
 ├─> BCLIBC_EngineT_initZeroCalculation
 ├─> BCLIBC_EngineT_integrate
 └─> BCLIBC_BaseTrajSeq_init / get_at / release

 Longest callstack:

 BCLIBC_EngineT_findZeroAngle
 -> BCLIBC_EngineT_initZeroCalculation
    -> BCLIBC_EngineT_findApex
       -> BCLIBC_EngineT_integrate
          -> eng->integrate_func_ptr
*/

namespace bclibc
{

#define BCLIBC_Engine_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, angle, y_out) \
    do                                                                    \
    {                                                                     \
        (status) = this->range_for_angle((angle), (y_out));               \
        if ((status) != BCLIBC_STATUS_SUCCESS)                            \
            return (status);                                              \
    } while (0)

    class BCLIBC_Engine : public BCLIBC_EngineT
    {

    public:
        void release_trajectory();

        BCLIBC_StatusCode integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            BCLIBC_TrajectoryDataFilter **data_filter,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason);

        BCLIBC_StatusCode integrate(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason);

        BCLIBC_StatusCode find_apex(
            BCLIBC_BaseTrajData *out);

        BCLIBC_StatusCode error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft,
            double *out_error_ft);

        BCLIBC_StatusCode init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData *result,
            BCLIBC_OutOfRangeError *error);

        BCLIBC_StatusCode zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error);

        BCLIBC_StatusCode zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error);

        BCLIBC_StatusCode range_for_angle(double angle_rad, double *result);

        BCLIBC_StatusCode find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS,
            BCLIBC_MaxRangeResult *result);

        BCLIBC_StatusCode find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error);
    };
};

#endif // BCLIBC_ENGINE_HPP
