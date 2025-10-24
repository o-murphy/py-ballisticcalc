# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from libc.string cimport strlen
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    Config_t,
    ShotProps_t,
    WindSock_t,
    TrajFlag_t,
    ErrorCode,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajData_t
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeq_t

# __all__ definitions belong in .pyx/.py files, not .pxd headers.


cdef extern from "include/engine.h" nogil:
    DEF MAX_ERR_MSG_LEN = 256

    ctypedef struct ZeroInitialData_t:
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

    # Forward declaration
    struct Engine_s

    # Typedef alias
    ctypedef Engine_s Engine_t

    # Declare the function signature type (not a pointer yet)
    ctypedef ErrorCode IntegrateFunc(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    ) noexcept nogil

    # Declare pointer to function
    ctypedef IntegrateFunc *IntegrateFuncPtr

    # Full struct definition
    struct Engine_s:
        int integration_step_count
        V3dT gravity_vector
        Config_t config
        ShotProps_t shot
        IntegrateFuncPtr integrate_func_ptr
        char err_msg[MAX_ERR_MSG_LEN]

    int isRangeError(ErrorCode err) noexcept nogil
    int isSequenceError(ErrorCode err) noexcept nogil

    void Engine_t_release_trajectory(Engine_t *eng) noexcept nogil

    ErrorCode Engine_t_integrate(
        Engine_t *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    ) noexcept nogil

    ErrorCode Engine_t_find_apex(
        Engine_t *eng,
        BaseTrajData_t *apex
    ) noexcept nogil

    ErrorCode Engine_t_error_at_distance(
        Engine_t *eng,
        double angle_rad,
        double target_x_ft,
        double target_y_ft,
        double *out_error_ft
    ) noexcept nogil

    ErrorCode Engine_t_init_zero_calculation(
        Engine_t *eng,
        double distance,
        double APEX_IS_MAX_RANGE_RADIANS,
        double ALLOWED_ZERO_ERROR_FEET,
        ZeroInitialData_t *result,
        OutOfRangeError_t *error
    ) noexcept nogil


cdef class CythonizedBaseIntegrationEngine:

    cdef:
        public object _config
        list _table_data  # list[object]
        Engine_t _engine

    cdef str get_error_message(CythonizedBaseIntegrationEngine self)

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
    cdef ErrorCode _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        double distance,
        ZeroInitialData_t *out,
    )
    cdef double _find_zero_angle(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
        double distance,
        bint lofted
    )
    cdef double _zero_angle(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
        double distance
    )
    cdef MaxRangeResult_t _find_max_range(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
        double low_angle_deg,
        double high_angle_deg,
    )
    cdef BaseTrajData_t _find_apex(
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
        TrajFlag_t filter_flags
    )

    cdef void _raise_on_input_error(CythonizedBaseIntegrationEngine self, ErrorCode err)
    cdef void _raise_on_integrate_error(CythonizedBaseIntegrationEngine self, ErrorCode err)
    cdef void _raise_on_apex_error(CythonizedBaseIntegrationEngine self, ErrorCode err)
    cdef void _raise_on_init_zero_error(
        CythonizedBaseIntegrationEngine self,
        ErrorCode err,
        OutOfRangeError_t *err_data
    )
