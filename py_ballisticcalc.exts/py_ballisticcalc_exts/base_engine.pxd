# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, BaseTrajData, TrajectoryData
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


cdef struct _TrajectoryDataFilter:
    int filter, current_flag, seen_zero
    double time_step, range_step
    double time_of_last_record, next_record_distance
    double previous_mach, previous_time
    V3dT previous_position, previous_velocity
    double previous_v_mach
    double look_angle

cdef _TrajectoryDataFilter createTrajectoryDataFilter(int filter_flags, double range_step,
                                                      const V3dT *initial_position_ptr,
                                                      const V3dT *initial_velocity_ptr,
                                                      double time_step = ?)
cdef void setup_seen_zero(_TrajectoryDataFilter * tdf, double height, const ShotData_t *shot_data_ptr)
cdef BaseTrajData should_record(_TrajectoryDataFilter * tdf,
                                const V3dT *position_ptr,
                                const V3dT *velocity_ptr,
                                double mach, double time)



cdef struct WindSock_t:
    Wind_t * winds
    int current
    int length
    double next_range
    V3dT last_vector_cache

# Function to create and initialize a WindSock_t
cdef WindSock_t * WindSockT_create(object winds_py_list)
# # Function to destroy (free memory) a WindSock_t
cdef void WindSockT_free(WindSock_t * wind_sock)
# # Helper functions that operate on WindSock_t
cdef V3dT WindSockT_current_vector(WindSock_t * wind_sock)
cdef void WindSockT_update_cache(WindSock_t * wind_sock)
cdef V3dT WindSockT_vector_for_range(WindSock_t * wind_sock, double next_range)


cdef class CythonizedBaseIntegrationEngine:
    cdef:
        list _table_data # list[object]
        V3dT gravity_vector
        public object _config
        WindSock_t * _wind_sock
        Config_t _config_s # Declared here
        ShotData_t _shot_s # Declared here

    # cdef void __dealloc__(CythonizedBaseIntegrationEngine self) # Uncomment if you want to declare __dealloc__
    cdef double get_calc_step(self, double step = ?)

    # Note: Properties are Python-level constructs and are not typically declared in .pxd files
    # unless you are exposing the underlying cdef attribute directly.
    # For _table_data, the declaration above (cdef list _table_data) makes it accessible.

    # Python 'def' methods are not exposed in the C interface defined by a .pxd.
    # Only 'cdef' or 'cpdef' methods are declared here.
    cdef void _free_trajectory(self)
    cdef void _init_trajectory(self, object shot_info)
    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance)
    cdef list _integrate(CythonizedBaseIntegrationEngine self,
                         double maximum_range, double record_step, int filter_flags, double time_step = ?)


cdef object create_trajectory_row(double time, const V3dT *range_vector_ptr, const V3dT *velocity_vector_ptr,
                                  double mach, const ShotData_t * shot_data_ptr,
                                  double density_factor, double drag, int flag)

cdef object _new_feet(double v)
cdef object _new_fps(double v)
cdef object _new_rad(double v)
cdef object _new_ft_lb(double v)
cdef object _new_lb(double v)
