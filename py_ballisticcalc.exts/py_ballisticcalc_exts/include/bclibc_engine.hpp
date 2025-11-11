#ifndef BCLIBC_ENGINE_HPP
#define BCLIBC_ENGINE_HPP

#include "bclibc_engine.h"
#include "bclibc_traj_filter.hpp"

namespace bclibc
{
    class BCLIBC_Engine : public BCLIBC_EngineT
    {

    public:
        void release_trajectory()
        {
            BCLIBC_EngineT_releaseTrajectory(
                this);
        };

        BCLIBC_StatusCode integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            BCLIBC_TrajectoryDataFilter **data_filter,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason)
        {
            if (!trajectory || !reason || !data_filter || !this->integrate_func_ptr)
            {
                BCLIBC_PUSH_ERR(&this->err_stack, BCLIBC_E_INPUT_ERROR, BCLIBC_SRC_INTEGRATE, "Invalid input (NULL pointer).");
                return BCLIBC_STATUS_ERROR;
            }

            BCLIBC_StatusCode status = this->integrate(
                range_limit_ft,
                range_step_ft,
                time_step,
                trajectory,
                reason);
            if (status == BCLIBC_STATUS_ERROR)
            {
                return BCLIBC_STATUS_ERROR;
            }

            BCLIBC_ErrorType err;
            BCLIBC_BaseTrajData temp_btd = BCLIBC_BaseTrajData_init();
            BCLIBC_BaseTrajData *init = &temp_btd;
            BCLIBC_BaseTrajData *fin = &temp_btd;

            err = BCLIBC_BaseTrajSeq_getItem(trajectory, 0, init);
            if (err != BCLIBC_E_NO_ERROR)
            {
                BCLIBC_PUSH_ERR(
                    &this->err_stack,
                    BCLIBC_E_INDEX_ERROR, BCLIBC_SRC_INTEGRATE,
                    "Unexpected failure retrieving element 0");
                return BCLIBC_STATUS_ERROR;
            }

            *data_filter = new BCLIBC_TrajectoryDataFilter(
                &this->shot,
                filter_flags,
                init->position,
                init->velocity,
                this->shot.barrel_elevation,
                this->shot.look_angle,
                range_limit_ft,
                range_step_ft,
                time_step);

            for (int i = 0; i < BCLIBC_BaseTrajSeq_len(trajectory); i++)
            {
                err = BCLIBC_BaseTrajSeq_getItem(trajectory, i, &temp_btd);
                if (err != BCLIBC_E_NO_ERROR)
                {
                    BCLIBC_PUSH_ERR(
                        &this->err_stack,
                        BCLIBC_E_INDEX_ERROR, BCLIBC_SRC_INTEGRATE,
                        "Unexpected failure retrieving element %d", i);
                    return BCLIBC_STATUS_ERROR;
                }
                (*data_filter)->record(&temp_btd);
            }

            if (*reason != BCLIBC_TERM_REASON_NO_TERMINATE)
            {
                err = BCLIBC_BaseTrajSeq_getItem(trajectory, -1, fin);
                if (err != BCLIBC_E_NO_ERROR)
                {
                    BCLIBC_PUSH_ERR(
                        &this->err_stack,
                        BCLIBC_E_INDEX_ERROR, BCLIBC_SRC_INTEGRATE,
                        "Unexpected failure retrieving element -1");
                    return BCLIBC_STATUS_ERROR;
                }

                if (fin->time > (*data_filter)->get_record(-1).time)
                {
                    BCLIBC_TrajectoryData temp_td = BCLIBC_TrajectoryData(
                        &this->shot,
                        fin->time,
                        &fin->position,
                        &fin->velocity,
                        fin->mach,
                        BCLIBC_TRAJ_FLAG_NONE);
                    (*data_filter)->append(&temp_td);
                }
            }
            return BCLIBC_STATUS_SUCCESS;
        };

        BCLIBC_StatusCode integrate(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason)
        {
            return BCLIBC_EngineT_integrate(
                this,
                range_limit_ft,
                range_step_ft,
                time_step,
                trajectory,
                reason);
        };

        BCLIBC_StatusCode find_apex(
            BCLIBC_BaseTrajData *out)
        {
            return BCLIBC_EngineT_findApex(
                this,
                out);
        };

        BCLIBC_StatusCode error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft,
            double *out_error_ft)
        {
            return BCLIBC_EngineT_errorAtDistance(
                this,
                angle_rad,
                target_x_ft,
                target_y_ft,
                out_error_ft);
        };

        BCLIBC_StatusCode init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData *result,
            BCLIBC_OutOfRangeError *error)
        {
            return BCLIBC_EngineT_initZeroCalculation(
                this,
                distance,
                APEX_IS_MAX_RANGE_RADIANS,
                ALLOWED_ZERO_ERROR_FEET,
                result,
                error);
        };

        BCLIBC_StatusCode zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error)
        {
            return BCLIBC_EngineT_zeroAngleWithFallback(
                this,
                distance,
                APEX_IS_MAX_RANGE_RADIANS,
                ALLOWED_ZERO_ERROR_FEET,
                result,
                range_error,
                zero_error);
        };

        BCLIBC_StatusCode zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error)
        {
            return BCLIBC_EngineT_zeroAngle(
                this,
                distance,
                APEX_IS_MAX_RANGE_RADIANS,
                ALLOWED_ZERO_ERROR_FEET,
                result,
                range_error,
                zero_error);
        };

        BCLIBC_StatusCode find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS,
            BCLIBC_MaxRangeResult *result)
        {
            return BCLIBC_EngineT_findMaxRange(
                this,
                low_angle_deg,
                high_angle_deg,
                APEX_IS_MAX_RANGE_RADIANS,
                result);
        };

        BCLIBC_StatusCode find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error)
        {
            return BCLIBC_EngineT_findZeroAngle(
                this,
                distance,
                lofted,
                APEX_IS_MAX_RANGE_RADIANS,
                ALLOWED_ZERO_ERROR_FEET,
                result,
                range_error,
                zero_error);
        };
    };
};

#endif // BCLIBC_ENGINE_HPP
