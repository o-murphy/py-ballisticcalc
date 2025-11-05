# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from libc.string cimport strlen
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_Config,
    BCLIBC_ShotProps,
    BCLIBC_WindSock,
    BCLIBC_TrajFlag,
    BCLIBC_BaseTrajData,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BCLIBC_BaseTrajSeq
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.error_stack cimport BCLIBC_ErrorStack, BCLIBC_StatusCode, BCLIBC_ErrorType, BCLIBC_ErrorFrame

# __all__ definitions belong in .pyx/.py files, not .pxd headers.


cdef extern from "include/bclibc_engine.h" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    ctypedef enum BCLIBC_ZeroInitialStatus:
        BCLIBC_ZERO_INIT_CONTINUE
        BCLIBC_ZERO_INIT_DONE

    ctypedef enum BCLIBC_TerminationReason:
        # Solver specific, not real errors, just termination reasons!
        BCLIBC_TERM_REASON_NO_TERMINATE
        BCLIBC_TERM_REASON_MINIMUM_VELOCITY_REACHED
        BCLIBC_TERM_REASON_MAXIMUM_DROP_REACHED
        BCLIBC_TERM_REASON_MINIMUM_ALTITUDE_REACHED

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
    struct BCLIBC_EngineT

    # Typedef alias
    ctypedef BCLIBC_EngineS BCLIBC_EngineT

    # Declare the function signature type (not a pointer yet)
    ctypedef BCLIBC_StatusCode BCLIBC_IntegrateFunc(
        BCLIBC_EngineT *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

    # Declare pointer to function
    ctypedef BCLIBC_IntegrateFunc *BCLIBC_IntegrateFuncPtr

    # Full struct definition
    struct BCLIBC_EngineS:
        int integration_step_count
        BCLIBC_V3dT gravity_vector
        BCLIBC_Config config
        BCLIBC_ShotProps shot
        BCLIBC_IntegrateFuncPtr integrate_func_ptr
        BCLIBC_ErrorStack err_stack

    void BCLIBC_EngineT_releaseTrajectory(BCLIBC_EngineT *eng) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_integrate(
        BCLIBC_EngineT *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_findApex(
        BCLIBC_EngineT *eng,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_errorAtDistance(
        BCLIBC_EngineT *eng,
        double angle_rad,
        double target_x_ft,
        double target_y_ft,
        double *out_error_ft
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_initZeroCalculation(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        BCLIBC_ZeroInitialData *result,
        BCLIBC_OutOfRangeError *error
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_zeroAngle(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_zeroAngleWithFallback(
        BCLIBC_EngineT *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_findMaxRange(
        BCLIBC_EngineT *eng,
        double low_angle_deg,
        double high_angle_deg,
        double APEX_IS_MAX_RANGE_RADIANS,
        BCLIBC_MaxRangeResult *result
    ) noexcept nogil

    BCLIBC_StatusCode BCLIBC_EngineT_findZeroAngle(
        BCLIBC_EngineT *eng,
        double distance,
        int lofted,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        double *result,
        BCLIBC_OutOfRangeError *range_error,
        BCLIBC_ZeroFindingError *zero_error
    ) noexcept nogil


cdef class CythonizedBaseIntegrationEngine:

    cdef:
        public object _config
        list _table_data  # list[object]
        BCLIBC_EngineT _engine

    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    # Note: Properties are Python-level constructs and are not typically declared in .pxd files
    # unless you are exposing the underlying cdef attribute directly.
    # For _table_data, the declaration above (cdef list _table_data) makes it accessible.

    # Python 'def' methods are not exposed in the C interface defined by a .pxd.
    # Only 'cdef' or 'cpdef' methods are declared here.
    cdef void _release_trajectory(CythonizedBaseIntegrationEngine self)

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
        double distance,
        bint lofted
    )
    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        double distance
    )
    cdef BCLIBC_MaxRangeResult _find_max_range(
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
