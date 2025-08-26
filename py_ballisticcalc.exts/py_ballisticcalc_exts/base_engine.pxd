# pxd for py_ballisticcalc_exts.base_engine

from py_ballisticcalc_exts.cy_bindings cimport Config_t, Wind_t, ShotProps_t
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
from py_ballisticcalc_exts.v3d cimport V3dT

# __all__ definitions belong in .pyx/.py files, not .pxd headers.

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

    double getCorrection(double distance, double offset)
    double calculateEnergy(double bulletWeight, double velocity)
    double calculateOgw(double bulletWeight, double velocity)


# Function to create and initialize a WindSock_t
cdef WindSock_t * WindSock_t_create(object winds_py_list) except NULL


cdef class CythonizedBaseIntegrationEngine:
    cdef:
        public int integration_step_count
        public object _config
        list _table_data  # list[object]
        V3dT gravity_vector
        WindSock_t * _wind_sock
        Config_t _config_s  # Declared here
        ShotProps_t _shot_s  # Declared here

    # cdef void __dealloc__(CythonizedBaseIntegrationEngine self) # Uncomment if you want to declare __dealloc__
    cdef double get_calc_step(CythonizedBaseIntegrationEngine self)

    # Note: Properties are Python-level constructs and are not typically declared in .pxd files
    # unless you are exposing the underlying cdef attribute directly.
    # For _table_data, the declaration above (cdef list _table_data) makes it accessible.

    # Python 'def' methods are not exposed in the C interface defined by a .pxd.
    # Only 'cdef' or 'cpdef' methods are declared here.
    cdef void _free_trajectory(CythonizedBaseIntegrationEngine self)
    cdef ShotProps_t* _init_trajectory(CythonizedBaseIntegrationEngine self, object shot_info)
    cdef tuple _init_zero_calculation(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance)
    cdef object _find_zero_angle(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance, bint lofted)
    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, double distance)
    cdef tuple _find_max_range(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr, tuple angle_bracket_deg = *)
    cdef BaseTrajDataT _find_apex(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr)
    cdef double _error_at_distance(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr,
                                   double angle_rad, double target_x_ft, double target_y_ft)
    # In contrast to Python engines, _integrate returns (CBaseTrajSeq, Optional[str]) as a Python tuple
    cdef tuple _integrate(CythonizedBaseIntegrationEngine self, ShotProps_t *shot_props_ptr,
                          double range_limit_ft, double range_step_ft, double time_step, int filter_flags)


cdef object create_trajectory_row(double time, const V3dT *range_vector_ptr, const V3dT *velocity_vector_ptr,
                                  double mach, const ShotProps_t * shot_props_ptr,
                                  double density_ratio, double drag, int flag)

cdef object _new_feet(double v)
cdef object _new_fps(double v)
cdef object _new_rad(double v)
cdef object _new_ft_lb(double v)
cdef object _new_lb(double v)
