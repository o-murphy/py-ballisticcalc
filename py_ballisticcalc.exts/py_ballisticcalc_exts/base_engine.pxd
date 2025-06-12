# pxd for py_ballisticcalc_exts.trajectory_calc_engine

from cython cimport final
from libc.math cimport fabs, sin, cos, tan, atan, atan2

from py_ballisticcalc_exts.vector cimport CVector
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, BaseTrajData, TrajectoryData
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    Wind_t,
    Atmosphere_t,
    ShotData_t,
    config_bind,
    cy_calculate_curve,
    cy_table_to_mach,
    cy_spin_drift,
    cy_drag_by_mach,
    cy_get_correction,
    cy_calculate_energy,
    cy_calculate_ogw,
    cy_update_stability_coefficient,
    free_trajectory,
    wind_to_c_vector,
)


__all__ = (
    'CythonizedBaseIntegrationEngine',
    '_WindSock',
    '_TrajectoryDataFilter',
    'create_trajectory_row',
)


@final
cdef class _TrajectoryDataFilter:
    cdef:
        int filter, current_flag, seen_zero
        # int current_item  # This variable was declared but unused in the original code. Keeping for completeness if it's meant to be used.
        double previous_mach, previous_time, previous_v_mach, next_record_distance
        double range_step, time_of_last_record, time_step, look_angle
        CVector previous_position, previous_velocity

    # Removed "-> None" as it's not standard for pxd signatures
    cdef void setup_seen_zero(_TrajectoryDataFilter self, double height, double barrel_elevation, double look_angle)
    cdef void clear_current_flag(_TrajectoryDataFilter self)
    cdef BaseTrajData should_record(_TrajectoryDataFilter self,
                            CVector position,
                            CVector velocity,
                            double mach,
                            double time)
    cdef void check_next_time(_TrajectoryDataFilter self, double time)
    cdef void check_mach_crossing(_TrajectoryDataFilter self, double velocity, double mach)
    cdef void check_zero_crossing(_TrajectoryDataFilter self, CVector range_vector)


@final
cdef class _WindSock:
    cdef:
        list winds # list[Wind_t]
        int current
        double next_range
        CVector _last_vector_cache
        int _length

    cdef CVector current_vector(_WindSock self)
    cdef void update_cache(_WindSock self)
    cdef CVector vector_for_range(_WindSock self, double next_range)


cdef class CythonizedBaseIntegrationEngine:
    cdef:
        list _table_data # list[object]
        CVector gravity_vector
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


cdef object create_trajectory_row(double time, CVector range_vector, CVector velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, int flag)

cdef object _new_feet(double v)
cdef object _new_fps(double v)
cdef object _new_rad(double v)
cdef object _new_ft_lb(double v)
cdef object _new_lb(double v)
