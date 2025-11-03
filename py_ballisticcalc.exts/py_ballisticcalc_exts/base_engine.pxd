# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from libc.string cimport strlen
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    Config_t,
    ShotProps_t,
    WindSock_t,
    BCLIBC_TrajFlag,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BCLIBC_BaseTrajData
from py_ballisticcalc_exts.base_traj_seq cimport BCLIBC_BaseTrajSeq
from py_ballisticcalc_exts.error_stack cimport BCLIBC_ErrorStack, BCLIBC_StatusCode, BCLIBC_ErrorType, BCLIBC_ErrorFrame

# __all__ definitions belong in .pyx/.py files, not .pxd headers.


cdef extern from "include/engine.h" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    ctypedef enum ZeroInitialStatus:
        ZERO_INIT_CONTINUE
        ZERO_INIT_DONE

    ctypedef enum TerminationReason:
        # Solver specific, not real errors, just termination reasons!
        NO_TERMINATE
        RANGE_ERROR_MINIMUM_VELOCITY_REACHED
        RANGE_ERROR_MAXIMUM_DROP_REACHED
        RANGE_ERROR_MINIMUM_ALTITUDE_REACHED

    ctypedef struct ZeroInitialData_t:
        ZeroInitialStatus status
        double look_angle_rad
        double slant_range_ft
        double target_x_ft
        double target_y_ft
        double start_height_ft

    ctypedef struct MaxRangeResult_t:
        double max_range_ft
        double angle_at_max_rad

    ctypedef struct OutOfRangeError_t:
        double requested_distance_ft
        double max_range_ft
        double look_angle_rad

    ctypedef struct ZeroFindingError_t:
        double zero_finding_error
        int iterations_count
        double last_barrel_elevation_rad

    # Forward declaration
    struct Engine_s

    # Typedef alias
    ctypedef Engine_s Engine_t

    # Declare the function signature type (not a pointer yet)
    ctypedef BCLIBC_StatusCode IntegrateFunc(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        TerminationReason *reason,
    ) noexcept nogil

    # Declare pointer to function
    ctypedef IntegrateFunc *IntegrateFuncPtr

    # Full struct definition
    struct Engine_s:
        int integration_step_count
        BCLIBC_V3dT gravity_vector
        Config_t config
        ShotProps_t shot
        IntegrateFuncPtr integrate_func_ptr
        BCLIBC_ErrorStack err_stack

    void Engine_t_release_trajectory(Engine_t *eng) noexcept nogil

    BCLIBC_StatusCode Engine_t_integrate(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        TerminationReason *reason,
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_find_apex(
        Engine_t *eng,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_error_at_distance(
        Engine_t *eng,
        double angle_rad,
        double target_x_ft,
        double target_y_ft,
        double *out_error_ft
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_init_zero_calculation(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        ZeroInitialData_t *result,
        OutOfRangeError_t *error
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_zero_angle(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        OutOfRangeError_t *range_error,
        ZeroFindingError_t *zero_error
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_zero_angle_with_fallback(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        OutOfRangeError_t *range_error,
        ZeroFindingError_t *zero_error
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_find_max_range(
        Engine_t *eng,
        double low_angle_deg,
        double high_angle_deg,
        double APEX_IS_MAX_RANGE_RADIANS,
        MaxRangeResult_t *result
    ) noexcept nogil

    BCLIBC_StatusCode Engine_t_find_zero_angle(
        Engine_t *eng,
        double distance,
        int lofted,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        OutOfRangeError_t *range_error,
        ZeroFindingError_t *zero_error
    ) noexcept nogil


cdef class CythonizedBaseIntegrationEngine:

    cdef:
        public object _config
        list _table_data  # list[object]
        Engine_t _engine

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    # Note: Properties are Python-level constructs and are not typically declared in .pxd files
    # unless you are exposing the underlying cdef attribute directly.
    # For _table_data, the declaration above (cdef list _table_data) makes it accessible.

    # Python 'def' methods are not exposed in the C interface defined by a .pxd.
    # Only 'cdef' or 'cpdef' methods are declared here.
    cdef void _release_trajectory(CythonizedBaseIntegrationEngine self)

    cdef ShotProps_t* _init_trajectory(
        CythonizedBaseIntegrationEngine self,
        object shot_info
    )
    cdef BCLIBC_StatusCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        ZeroInitialData_t *out,
    )
    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        double distance,
        bint lofted
    )
    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        double distance
    )
    cdef MaxRangeResult_t _find_max_range(
        CythonizedBaseIntegrationEngine self,
        double low_angle_deg,
        double high_angle_deg,
    )
    cdef BCLIBC_BaseTrajData _find_apex(
        CythonizedBaseIntegrationEngine self,
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
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags
    )

    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        BCLIBC_ErrorFrame *err,
        OutOfRangeError_t *err_data
    )
    cdef void _raise_on_zero_finding_error(
        CythonizedBaseIntegrationEngine self,
        BCLIBC_ErrorFrame *err,
        ZeroFindingError_t *zero_error
    )
    cdef void _raise_solver_runtime_error(CythonizedBaseIntegrationEngine self, BCLIBC_ErrorFrame *err)
