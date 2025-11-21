#ifndef BCLIBC_ENGINE_HPP
#define BCLIBC_ENGINE_HPP

#include "bclibc/error_stack.hpp"
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
    enum class BCLIBC_ZeroInitialStatus
    {
        CONTINUE,
        DONE,
    };

    enum class BCLIBC_TerminationReason
    {
        // Solver specific flags (always include RANGE_ERROR)
        NO_TERMINATE,
        MINIMUM_VELOCITY_REACHED,
        MAXIMUM_DROP_REACHED,
        MINIMUM_ALTITUDE_REACHED,
    };

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

    struct BCLIBC_MaxRangeResult
    {
        double max_range_ft;
        double angle_at_max_rad;
    };

    typedef struct
    {
        double zero_finding_error;
        int iterations_count;
        double last_barrel_elevation_rad;
    } BCLIBC_ZeroFindingError;

    class BCLIBC_Engine;

    using BCLIBC_IntegrateFunc = void(
        BCLIBC_Engine &eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason);

    using BCLIBC_IntegrateFuncPtr = BCLIBC_IntegrateFunc *;

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
        void integrate(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason);

        void integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            std::vector<BCLIBC_TrajectoryData> &records,
            BCLIBC_TerminationReason &reason,
            BCLIBC_BaseTrajSeq *dense_trajectory);

        void find_apex(BCLIBC_BaseTrajData &apex_out);

        double error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft);

        void init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData &result,
            BCLIBC_OutOfRangeError &error);

        BCLIBC_StatusCode zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double &result,
            BCLIBC_OutOfRangeError &range_error,
            BCLIBC_ZeroFindingError &zero_error);

        BCLIBC_StatusCode zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double &result,
            BCLIBC_OutOfRangeError &range_error,
            BCLIBC_ZeroFindingError &zero_error);

        double range_for_angle(double angle_rad);

        BCLIBC_MaxRangeResult find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS);

        BCLIBC_StatusCode find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double &result,
            BCLIBC_OutOfRangeError &range_error,
            BCLIBC_ZeroFindingError &zero_error);

    private:
        inline void integrate_func_ptr_not_null();
    };
};

#endif // BCLIBC_ENGINE_HPP
