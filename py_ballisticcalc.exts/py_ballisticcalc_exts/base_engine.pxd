# pxd for py_ballisticcalc_exts.base_engine

from libcpp.vector cimport vector
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_Config,
    BCLIBC_ShotProps,
    BCLIBC_WindSock,
    BCLIBC_TrajFlag,
    BCLIBC_TerminationReason,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport (
    BCLIBC_BaseTrajSeq,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
    BCLIBC_BaseTrajData_InterpKey,
    BCLIBC_BaseTrajDataHandlerInterface
)
from py_ballisticcalc_exts.exceptions cimport raise_solver_exception


cdef extern from "<functional>" namespace "std":
    cdef cppclass function[F]:
        function() except +
        function(F *f_ptr) except +
        function(const function[F]& other) except +
        function(function[F]&& other)
        function[F]& operator=(F *f_ptr) except +
        function[F]& operator=(const function[F]& other) except +
        function[F]& operator=(function[F]&& other)
        bint operator bool() const


cdef extern from "include/bclibc/engine.hpp" namespace "bclibc" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    cdef enum class BCLIBC_ZeroInitialStatus:
        CONTINUE
        DONE

    cdef cppclass BCLIBC_ZeroInitialData:
        BCLIBC_ZeroInitialStatus status
        double look_angle_rad
        double slant_range_ft
        double target_x_ft
        double target_y_ft
        double start_height_ft

    cdef cppclass BCLIBC_MaxRangeResult:
        double max_range_ft
        double angle_at_max_rad

    # Forward declaration
    cdef cppclass BCLIBC_BaseEngine

    # Declare the function signature type (not a pointer yet)
    ctypedef void BCLIBC_IntegrateFunc(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &trajectory,
        BCLIBC_TerminationReason &reason,
    ) except +

    # Declare function
    ctypedef function[BCLIBC_IntegrateFunc] BCLIBC_IntegrateCallable

    cdef cppclass BCLIBC_BaseEngine:
        int integration_step_count
        BCLIBC_V3dT gravity_vector
        BCLIBC_Config config
        BCLIBC_ShotProps shot
        BCLIBC_IntegrateCallable integrate_func

        BCLIBC_BaseEngine() except+

        void integrate(
            double range_limit_ft,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason) except +raise_solver_exception

        void integrate_at(
            BCLIBC_BaseTrajData_InterpKey key,
            double target_value,
            BCLIBC_BaseTrajData &raw_data,
            BCLIBC_TrajectoryData &full_data) except +raise_solver_exception

        void integrate_filtered(
            double range_limit_ft,
            double range_step_ft,
            double time_step,
            BCLIBC_TrajFlag filter_flags,
            vector[BCLIBC_TrajectoryData] &records,
            BCLIBC_TerminationReason &reason,
            BCLIBC_BaseTrajSeq *dense_trajectory) except +raise_solver_exception

        void find_apex(BCLIBC_BaseTrajData &apex_out) except +raise_solver_exception

        double error_at_distance(
            double angle_rad,
            double target_x_ft,
            double target_y_ft) except +raise_solver_exception

        BCLIBC_MaxRangeResult find_max_range(
            double low_angle_deg,
            double high_angle_deg,
            double APEX_IS_MAX_RANGE_RADIANS) except +raise_solver_exception

        void init_zero_calculation(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET,
            BCLIBC_ZeroInitialData &result) except +raise_solver_exception

        double zero_angle_with_fallback(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET) except +raise_solver_exception

        double zero_angle(
            double distance,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET) except +raise_solver_exception

        double find_zero_angle(
            double distance,
            int lofted,
            double APEX_IS_MAX_RANGE_RADIANS,
            double ALLOWED_ZERO_ERROR_FEET) except +raise_solver_exception

cdef class CythonizedBaseIntegrationEngine:

    cdef double _DEFAULT_TIME_STEP

    cdef:
        public object _config
        list[object] _table_data  # list[object]
        BCLIBC_BaseEngine _this

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef void _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        BCLIBC_ZeroInitialData &out,
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
    cdef BCLIBC_TrajectoryData _find_apex(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        double angle_rad,
        double target_x_ft,
        double target_y_ft
    )

    cdef void _integrate_raw_at(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        BCLIBC_BaseTrajData_InterpKey key,
        double target_value,
        BCLIBC_BaseTrajData &raw_data,
        BCLIBC_TrajectoryData &full_data
    )

    cdef void _integrate(
        CythonizedBaseIntegrationEngine self,
        object shot_info,
        double range_limit_ft,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    )
