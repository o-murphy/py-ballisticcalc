#ifndef BCLIBC_ENGINE_HPP
#define BCLIBC_ENGINE_HPP

#include <mutex>
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

    struct BCLIBC_ZeroInitialData
    {
        BCLIBC_ZeroInitialStatus status;
        double look_angle_rad;
        double slant_range_ft;
        double target_x_ft;
        double target_y_ft;
        double start_height_ft;
    };

    struct BCLIBC_MaxRangeResult
    {
        double max_range_ft;
        double angle_at_max_rad;
    };

    class BCLIBC_Engine;

    using BCLIBC_IntegrateFunc = void(
        BCLIBC_Engine &eng,
        double time_step,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason);

    using BCLIBC_IntegrateFuncPtr = BCLIBC_IntegrateFunc *;

    class BCLIBC_Engine
    {
        static constexpr double MAX_INTEGRATION_RANGE = 9e9;

    private:
        // A recursive mutex that guarantees thread-safe access (read/write) to the entire Engine state,
        // specifically `config` and `shot`. The recursive nature is necessary because public methods
        // (like zero_angle) call other internal methods (like integrate), requiring nested locking.
        std::recursive_mutex engine_mutex;

    public:
        int integration_step_count;
        BCLIBC_V3dT gravity_vector;
        BCLIBC_Config config;
        BCLIBC_ShotProps shot;
        BCLIBC_IntegrateFuncPtr integrate_func_ptr;

    public:
        /**
         * @brief Calls the underlying integration function for the projectile trajectory.
         *
         * @param time_step Integration timestep in seconds.
         * @param handler Reference to a data handler for trajectory recording.
         * @param reason Reference to store termination reason.
         *
         * @throws std::logic_error if integrate_func_ptr is null.
         */
        void integrate(
            double range_limit_ft,
            double time_step,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason);

        /**
         * @brief Performs trajectory integration and interpolates a single data point
         * where a specific key attribute reaches a target value.
         *
         * This method runs a full trajectory integration internally, using
         * BCLIBC_SinglePointHandler to find and interpolate the point where the
         * specified key (e.g., 'time', 'mach', 'position.z') equals the target value.
         * The integration runs up to MAX_INTEGRATION_RANGE using a default timestep (0.0).
         *
         * @param key The interpolation key (e.g., time, altitude, vector component)
         * to use as the independent variable.
         * @param target_value The value the key attribute must reach for the
         * integration to terminate and interpolation to occur.
         * @param raw_data Reference to a BCLIBC_BaseTrajData object that will store
         * the interpolated raw data point upon success.
         * @param full_data Reference to a BCLIBC_TrajectoryData object that will store
         * the full (processed) interpolated data point upon success.
         *
         * @note Access to the engine is protected by engine_mutex.
         * @warning The integration is performed with time_step = 0.0, implying that
         * the actual step size is determined internally by the integrator.
         *
         * @throws std::logic_error if integrate_func_ptr is null.
         * @throws BCLIBC_InterceptionError if the target point is not found within the
         * integrated trajectory (e.g., "No apex flagged...").
         */
        void integrate_at(
            BCLIBC_BaseTrajData_InterpKey key,
            double target_value,
            BCLIBC_BaseTrajData &raw_data,
            BCLIBC_TrajectoryData &full_data);

        /**
         * @brief Integrates the projectile trajectory using filters and optional dense trajectory storage.
         *
         * @param range_limit_ft Maximum range for integration in feet.
         * @param range_step_ft Step size along the range in feet for recording data.
         * @param time_step Integration timestep in seconds.
         * @param filter_flags Flags specifying which trajectory points to record.
         * @param records Vector to store filtered trajectory data.
         * @param reason Reference to store the termination reason.
         * @param dense_trajectory Optional pointer to store full dense trajectory data.
         *
         * @throws std::logic_error if integrate_func_ptr is null.
         */
        void integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            std::vector<BCLIBC_TrajectoryData> &records,
            BCLIBC_TerminationReason &reason,
            BCLIBC_BaseTrajSeq *dense_trajectory);

        /**
         * @brief Finds the apex (highest point) of the trajectory.
         *
         * @param apex_out Output variable to store apex trajectory data.
         *
         * @throws std::invalid_argument if barrel elevation is <= 0.
         * @throws BCLIBC_ZeroFindingError if apex cannot be determined.
         */
        void find_apex(BCLIBC_BaseTrajData &apex_out);

        /**
         * @brief Computes the vertical error at a specific horizontal distance.
         *
         * @param angle_rad Barrel elevation angle in radians.
         * @param target_x_ft Horizontal distance to target in feet.
         * @param target_y_ft Target height in feet.
         *
         * @return Vertical error in feet, corrected for horizontal offset.
         *
         * @throws std::out_of_range if trajectory data is invalid.
         * @throws BCLIBC_SolverRuntimeError if trajectory is too short.
         */
        double error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft);

        /**
         * @brief Initializes the zero-calculation routine for aiming.
         *
         * @param distance Slant distance to the target in feet.
         * @param APEX_IS_MAX_RANGE_RADIANS Threshold in radians to consider vertical shots.
         * @param ALLOWED_ZERO_ERROR_FEET Allowed range error in feet.
         * @param result Output structure with initial zero-finding data.
         *
         * @throws std::out_of_range if trajectory data is invalid.
         * @throws BCLIBC_OutOfRangeError if apex_slant_ft < result.slant_range_ft.
         *
         * Handles edge cases like very close or vertical shots.
         */
        void init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData &result);

        /**
         * @brief Finds the maximum range and corresponding angle for the current shot.
         *
         * @param low_angle_deg Lower bound of angle search in degrees.
         * @param high_angle_deg Upper bound of angle search in degrees.
         * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
         *
         * @return Structure containing maximum range (ft) and angle (rad).
         */
        BCLIBC_MaxRangeResult find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS);

        /**
         * @brief Attempts to compute zero angle and falls back to guaranteed method if primary fails.
         *
         * @param distance Target slant distance in feet.
         * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
         * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
         *
         * @return Zero angle (barrel elevation) in radians.
         */
        double zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET);

        /**
         * @brief Computes the zero angle for a given target distance.
         *
         * @param distance Target slant distance in feet.
         * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
         * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
         *
         * @return Zero angle (barrel elevation) in radians.
         *
         * @throws BCLIBC_ZeroFindingError if zero-finding fails to converge.
         */
        double zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET);

        /**
         * @brief Computes the range corresponding to a given barrel elevation angle.
         *
         * @param angle_rad Barrel elevation angle in radians.
         *
         * @return Slant distance in feet where the projectile crosses the line-of-sight.
         */
        double range_for_angle(double angle_rad);

        /**
         * @brief Finds the zero angle using Ridder's method.
         *
         * @param distance Target slant distance in feet.
         * @param lofted Non-zero if a lofted trajectory is allowed.
         * @param APEX_IS_MAX_RANGE_RADIANS Threshold for vertical shots in radians.
         * @param ALLOWED_ZERO_ERROR_FEET Maximum allowable error in feet.
         *
         * @return Zero angle (barrel elevation) in radians.
         *
         * @throws BCLIBC_OutOfRangeError if slant_range_ft > max_range_ft.
         * @throws BCLIBC_ZeroFindingError if zero-finding fails.
         */
        double find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET);

    private:
        /**
         * @brief Ensures the integration function pointer is valid.
         *
         * @throws std::logic_error if integrate_func_ptr is null.
         */
        inline void integrate_func_ptr_not_null();
    };
}; // namespace bclibc

#endif // BCLIBC_ENGINE_HPP
