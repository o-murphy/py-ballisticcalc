#ifndef BCLIBC_ENGINE_HPP
#define BCLIBC_ENGINE_HPP

#include "bclibc/traj_filter.hpp"

/*
Possible call chains:

BCLIBC_Engine.find_zero_angle
 ├─> BCLIBC_Engine.init_zero_calculation
 │    └─> BCLIBC_Engine.find_apex
 │         └─> BCLIBC_Engine.integrate
 │              └─> eng->integrate_func_ptr
 ├─> BCLIBC_Engine.find_max_range
 │    ├─> BCLIBC_Engine.find_apex
 │    │    └─> BCLIBC_Engine.integrate
 │    │         └─> eng->integrate_func_ptr
 │    └─> BCLIBC_Engine.range_for_angle
 │         └─> BCLIBC_Engine.integrate
 │              └─> eng->integrate_func_ptr
 └─> BCLIBC_Engine.error_at_distance
      └─> BCLIBC_Engine.integrate
      └─> BCLIBC_BaseTrajSeq / get_at / get_raw_item

BCLIBC_Engine.zero_angle
 ├─> BCLIBC_Engine.init_zero_calculation
 ├─> BCLIBC_Engine.integrate
 └─> BCLIBC_BaseTrajSeq / get_at / release

 Longest callstack:

 BCLIBC_Engine.find_zero_angle
 -> BCLIBC_Engine.init_zero_calculation
    -> BCLIBC_Engine.find_apex
       -> BCLIBC_Engine.integrate
          -> eng->integrate_func_ptr
*/

namespace bclibc
{
    typedef enum
    {
        BCLIBC_ZERO_INIT_CONTINUE,
        BCLIBC_ZERO_INIT_DONE,
    } BCLIBC_ZeroInitialStatus;

    typedef enum
    {
        // Solver specific flags (always include RANGE_ERROR)
        BCLIBC_TERM_REASON_NO_TERMINATE,
        BCLIBC_TERM_REASON_MINIMUM_VELOCITY_REACHED,
        BCLIBC_TERM_REASON_MAXIMUM_DROP_REACHED,
        BCLIBC_TERM_REASON_MINIMUM_ALTITUDE_REACHED,
    } BCLIBC_TerminationReason;

    typedef struct
    {
        BCLIBC_ZeroInitialStatus status;
        double look_angle_rad;
        double slant_range_ft;
        double target_x_ft;
        double target_y_ft;
        double start_height_ft;
    } BCLIBC_ZeroInitialData;

    typedef struct
    {
        double requested_distance_ft;
        double max_range_ft;
        double look_angle_rad;
    } BCLIBC_OutOfRangeError;

    typedef struct
    {
        double max_range_ft;
        double angle_at_max_rad;
    } BCLIBC_MaxRangeResult;

    typedef struct
    {
        double zero_finding_error;
        int iterations_count;
        double last_barrel_elevation_rad;
    } BCLIBC_ZeroFindingError;

    class BCLIBC_Engine;

    typedef BCLIBC_StatusCode BCLIBC_IntegrateFunc(
        BCLIBC_Engine *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajSeq *trajectory,
        BCLIBC_TerminationReason *reason);

    typedef BCLIBC_IntegrateFunc *BCLIBC_IntegrateFuncPtr;

    class BCLIBC_Engine
    {

    public:
        int integration_step_count;
        BCLIBC_V3dT gravity_vector;
        BCLIBC_Config config;
        BCLIBC_ShotProps shot;
        BCLIBC_IntegrateFuncPtr integrate_func_ptr;
        BCLIBC_ErrorStack err_stack;

    public:
        void release_trajectory();

        BCLIBC_StatusCode integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            std::vector<BCLIBC_TrajectoryData> *records,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason);

        BCLIBC_StatusCode integrate_dense(
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

#define BCLIBC_Engine_TRY_RANGE_FOR_ANGLE_OR_RETURN(status, angle, y_out) \
    do                                                                    \
    {                                                                     \
        (status) = this->range_for_angle((angle), (y_out));               \
        if ((status) != BCLIBC_STATUS_SUCCESS)                            \
            return (status);                                              \
    } while (0)
};

#endif // BCLIBC_ENGINE_HPP
