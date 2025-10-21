# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    Config_t,
    ShotProps_t,
    WindSock_t,
    TrajFlag_t,
    TerminationReason,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeq_t

# __all__ definitions belong in .pyx/.py files, not .pxd headers.


cdef extern from "include/engine.h" nogil:
    ctypedef struct ZeroInitialData_t:
        int status
        double look_angle_rad
        double slant_range_ft
        double target_x_ft
        double target_y_ft
        double start_height_ft

    ctypedef struct MaxRangeResult_t:
        double max_range_ft
        double angle_at_max_rad

    ctypedef struct AngleBracketDeg_t:
        double low_angle_deg
        double high_angle_deg

    # Forward declaration
    struct engine_t

    # Typedef alias
    ctypedef engine_t Engine_t

    # # Function pointer
    # ctypedef TerminationReason (*IntegrateFuncPtr)(
    #     Engine_t *engine_ptr,
    #     double range_limit_ft,
    #     double range_step_ft,
    #     double time_step,
    #     TrajFlag_t filter_flags,
    #     BaseTrajSeq_t *traj_seq_ptr
    # )

    # Declare the function signature type (not a pointer yet)
    ctypedef TerminationReason IntegrateFunc(
        Engine_t *engine_ptr,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    )
    
    # Declare pointer to function
    ctypedef IntegrateFunc *IntegrateFuncPtr

    # Full struct definition
    struct engine_t:
        int integration_step_count
        V3dT gravity_vector
        Config_t config
        ShotProps_t shot
        IntegrateFuncPtr integrate_func_ptr

    void Engine_t_release_trajectory(Engine_t *engine_ptr)

    TerminationReason Engine_t_integrate(
        Engine_t *engine_ptr,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    )


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
    cdef ZeroInitialData_t _init_zero_calculation(
        CythonizedBaseIntegrationEngine self,
        const ShotProps_t *shot_props_ptr,
        double distance
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
        AngleBracketDeg_t angle_bracket_deg
    )
    cdef BaseTrajDataT _find_apex(
        CythonizedBaseIntegrationEngine self,
        const ShotProps_t *shot_props_ptr
    )
    cdef double _error_at_distance(
        CythonizedBaseIntegrationEngine self,
        ShotProps_t *shot_props_ptr,
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
