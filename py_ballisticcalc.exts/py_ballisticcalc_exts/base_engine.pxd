# pxd for py_ballisticcalc_exts.base_engine

from libcpp.vector cimport vector
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_Config,
    BCLIBC_ShotProps,
    BCLIBC_WindSock,
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajSeq, BCLIBC_BaseTrajData, BCLIBC_TrajectoryData, BCLIBC_BaseTrajHandlerInterface
from py_ballisticcalc_exts.error_stack cimport BCLIBC_ErrorStack, BCLIBC_StatusCode, BCLIBC_ErrorType, BCLIBC_ErrorFrame


cdef extern from "include/bclibc/engine.hpp" namespace "bclibc" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    cdef enum class BCLIBC_ZeroInitialStatus:
        CONTINUE
        DONE

    cdef enum class BCLIBC_TerminationReason:
        # Solver specific, not real errors, just termination reasons!
        NO_TERMINATE
        MINIMUM_VELOCITY_REACHED
        MAXIMUM_DROP_REACHED
        MINIMUM_ALTITUDE_REACHED

    ctypedef struct BCLIBC_ZeroInitialData:
        BCLIBC_ZeroInitialStatus status
        double look_angle_rad
        double slant_range_ft
        double target_x_ft
        double target_y_ft
        double start_height_ft

    ctypedef struct BCLIBC_MaxRangeResult:
        double max_range_ft
        double angle_at_max_rad

    ctypedef struct BCLIBC_OutOfRangeError:
        double requested_distance_ft
        double max_range_ft
        double look_angle_rad

    ctypedef struct BCLIBC_ZeroFindingError:
        double zero_finding_error
        int iterations_count
        double last_barrel_elevation_rad

    # Forward declaration
    cdef cppclass BCLIBC_Engine

    # Declare the function signature type (not a pointer yet)
    ctypedef BCLIBC_StatusCode BCLIBC_IntegrateFunc(
        BCLIBC_Engine *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajHandlerInterface *trajectory,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

    # Declare pointer to function
    ctypedef BCLIBC_IntegrateFunc *BCLIBC_IntegrateFuncPtr

    cdef cppclass BCLIBC_Engine:
        int integration_step_count
        BCLIBC_V3dT gravity_vector
        BCLIBC_Config config
        BCLIBC_ShotProps shot
        BCLIBC_IntegrateFuncPtr integrate_func_ptr
        BCLIBC_ErrorStack err_stack

        BCLIBC_StatusCode integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            vector[BCLIBC_TrajectoryData] *records,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason) except +

        BCLIBC_StatusCode integrate_dense(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_BaseTrajSeq *trajectory,
            BCLIBC_TerminationReason *reason) noexcept nogil

        BCLIBC_StatusCode find_apex(
            BCLIBC_BaseTrajData *out) noexcept nogil

        BCLIBC_StatusCode error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft,
            double *out_error_ft) noexcept nogil

        BCLIBC_StatusCode init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData *result,
            BCLIBC_OutOfRangeError *error) noexcept nogil

        BCLIBC_StatusCode zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error) noexcept nogil

        BCLIBC_StatusCode zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error) noexcept nogil

        BCLIBC_StatusCode find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS,
            BCLIBC_MaxRangeResult *result) noexcept nogil

        BCLIBC_StatusCode find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            double *result,
            BCLIBC_OutOfRangeError *range_error,
            BCLIBC_ZeroFindingError *zero_error) noexcept nogil

cdef class CythonizedBaseIntegrationEngine:

    cdef:
        public object _config
        list[object] _table_data  # list[object]
        BCLIBC_Engine _this

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef BCLIBC_StatusCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        BCLIBC_ZeroInitialData *out,
    )
    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance,
        bint lofted
    )
    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double distance
    )
    cdef BCLIBC_MaxRangeResult _find_max_range(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double low_angle_deg,
        double high_angle_deg,
    )
    cdef BCLIBC_BaseTrajData _find_apex(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        double angle_rad,
        double target_x_ft,
        double target_y_ft
    )
    # In contrast to Python engines, _integrate returns (BaseTrajSeqT, Optional[str]) as a Python tuple
    cdef tuple _integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
    )

    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *err,
        const BCLIBC_OutOfRangeError *err_data
    )
    cdef void _raise_on_zero_finding_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *err,
        const BCLIBC_ZeroFindingError *zero_error
    )
    cdef void _raise_solver_runtime_error(
        CythonizedBaseIntegrationEngine self,
        const BCLIBC_ErrorFrame *err
    )


cdef list TrajectoryData_list_from_cpp(const vector[BCLIBC_TrajectoryData] *records)
cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
