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
    '_WindSock',
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
                                                      V3dT initial_position, V3dT initial_velocity,
                                                      double time_step = ?)
cdef void setup_seen_zero(_TrajectoryDataFilter * tdf, double height, double barrel_elevation, double look_angle)
cdef BaseTrajData should_record(_TrajectoryDataFilter * tdf, V3dT position, V3dT velocity, double mach, double time)


@final
cdef class _WindSock:
    cdef:
        list winds # list[Wind_t]
        int current
        double next_range
        V3dT _last_vector_cache
        int _length

    cdef V3dT current_vector(_WindSock self)
    cdef void update_cache(_WindSock self)
    cdef V3dT vector_for_range(_WindSock self, double next_range)


cdef class CythonizedBaseIntegrationEngine:
    cdef:
        list _table_data # list[object]
        V3dT gravity_vector
        public object _config
        _WindSock ws
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


cdef object create_trajectory_row(double time, V3dT range_vector, V3dT velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, int flag)

cdef object _new_feet(double v)
cdef object _new_fps(double v)
cdef object _new_rad(double v)
cdef object _new_ft_lb(double v)
cdef object _new_lb(double v)
