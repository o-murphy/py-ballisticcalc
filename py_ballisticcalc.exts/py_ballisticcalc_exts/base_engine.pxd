# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    Wind_t,
    ShotData_t,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)

__all__ = (
    'CythonizedBaseIntegrationEngine',
    'create_trajectory_row',
)

cdef extern from "include/bclib.h" nogil:

    cdef const double cMaxWindDistanceFeet

    ctypedef struct WindSock_t:
        Wind_t * winds
        int current
        int length
        double next_range
        V3dT last_vector_cache

    void WindSock_t_free(WindSock_t *ws)
    V3dT WindSock_t_currentVector(WindSock_t *wind_sock)
    int WindSock_t_updateCache(WindSock_t *ws)
    V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param)

    ctypedef struct TrajDataFilter_t:
        int filter, current_flag, seen_zero
        double time_step, range_step
        double time_of_last_record, next_record_distance
        double previous_mach, previous_time
        V3dT previous_position, previous_velocity
        double previous_v_mach
        double look_angle

    double getCorrection(double distance, double offset)
    double calculateEnergy(double bulletWeight, double velocity)
    double calculateOgw(double bulletWeight, double velocity)


cdef TrajDataFilter_t TrajDataFilter_t_create(int filter_flags, double range_step,
                                              const V3dT *initial_position_ptr,
                                              const V3dT *initial_velocity_ptr,
                                              double time_step = ?)
cdef void TrajDataFilter_t_setup_seen_zero(TrajDataFilter_t * tdf, double height, const ShotData_t *shot_data_ptr)
cdef BaseTrajData TrajDataFilter_t_should_record(TrajDataFilter_t * tdf,
                                                 const V3dT *position_ptr,
                                                 const V3dT *velocity_ptr,
                                                 double mach, double time)


# Function to create and initialize a WindSock_t
cdef WindSock_t * WindSock_t_create(object winds_py_list)


cdef class CythonizedBaseIntegrationEngine:
    cdef:
        public int integration_step_count
        public object _config
        list _table_data # list[object]
        V3dT gravity_vector
        WindSock_t * _wind_sock
        Config_t _config_s # Declared here
        ShotData_t _shot_s # Declared here

    # cdef void __dealloc__(CythonizedBaseIntegrationEngine self) # Uncomment if you want to declare __dealloc__
    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    # Note: Properties are Python-level constructs and are not typically declared in .pxd files
    # unless you are exposing the underlying cdef attribute directly.
    # For _table_data, the declaration above (cdef list _table_data) makes it accessible.

    # Python 'def' methods are not exposed in the C interface defined by a .pxd.
    # Only 'cdef' or 'cpdef' methods are declared here.
    cdef void _free_trajectory(CythonizedBaseIntegrationEngine self)
    cdef void _init_trajectory(CythonizedBaseIntegrationEngine self, object shot_info)
    cdef tuple _init_zero_calculation(CythonizedBaseIntegrationEngine self, object shot_info, object distance)
    cdef object _find_zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance, bint lofted)
    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance)
    cdef tuple _find_max_range(CythonizedBaseIntegrationEngine self, object shot_info, tuple angle_bracket_deg = *)
    cdef object _find_apex(CythonizedBaseIntegrationEngine self, object shot_info)
    # In contrast to Python engines, _integrate here returns (list[TrajectoryData], Optional[RangeError])
    cdef object _integrate(CythonizedBaseIntegrationEngine self,
                           double range_limit_ft, double range_step_ft, double time_step,
                           int filter_flags, bint dense_output)


cdef object create_trajectory_row(double time, const V3dT *range_vector_ptr, const V3dT *velocity_vector_ptr,
                                  double mach, const ShotData_t * shot_data_ptr,
                                  double density_ratio, double drag, int flag)

cdef object _new_feet(double v)
cdef object _new_fps(double v)
cdef object _new_rad(double v)
cdef object _new_ft_lb(double v)
cdef object _new_lb(double v)
