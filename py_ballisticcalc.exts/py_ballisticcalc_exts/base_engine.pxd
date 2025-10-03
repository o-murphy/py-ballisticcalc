# pxd for py_ballisticcalc_exts.base_engine

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport Config_t, Wind_t, ShotProps_t, Coriolis_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

# __all__ definitions belong in .pyx/.py files, not .pxd headers.

cdef extern from "include/bclib.h" nogil:

    cdef const double cMaxWindDistanceFeet

    ctypedef struct Config_t:
        double cStepMultiplier
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

    ctypedef struct CurvePoint_t:
        double a
        double b
        double c
        double d

    ctypedef struct Curve_t:
        CurvePoint_t *points
        size_t length

    void Curve_t_free(Curve_t *curve_ptr)

    ctypedef struct MachList_t:
        double * array
        size_t length

    void MachList_t_free(MachList_t *mach_list_ptr)

    ctypedef struct Atmosphere_t:
        double _t0
        double _a0
        double _p0
        double _mach
        double density_ratio
        double cLowestTempC

    void Atmosphere_t_updateDensityFactorAndMachForAltitude(
        const Atmosphere_t *atmo_ptr,
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr) noexcept nogil

    ctypedef struct Coriolis_t:
        double sin_lat
        double cos_lat
        double sin_az
        double cos_az
        double range_east
        double range_north
        double cross_east
        double cross_north
        int flat_fire_only
        double muzzle_velocity_fps

    ctypedef struct ShotProps_t:
        double bc
        Curve_t curve
        MachList_t mach_list
        double look_angle
        double twist
        double length
        double diameter
        double weight
        double barrel_elevation
        double barrel_azimuth
        double sight_height
        double cant_cosine
        double cant_sine
        double alt0
        double calc_step
        double muzzle_velocity
        double stability_coefficient
        int filter_flags
        Atmosphere_t atmo
        Coriolis_t coriolis

    void ShotProps_t_free(ShotProps_t *shot_props_ptr) noexcept nogil
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time) noexcept nogil
    int ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr) noexcept nogil
    double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach) noexcept nogil

    double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                       const Curve_t *curve_ptr,
                                       double mach) noexcept nogil

    ctypedef struct Wind_t:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr)

    ctypedef enum TrajFlag_t:
        NONE = 0
        ZERO_UP = 1
        ZERO_DOWN = 2
        ZERO = ZERO_UP | ZERO_DOWN
        MACH = 4
        RANGE = 8
        APEX = 16
        ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX

    ctypedef struct BaseTrajData_t:
        double time
        V3dT position
        V3dT velocity
        double mach

    ctypedef struct WindSock_t:
        Wind_t *winds
        int current
        int length
        double next_range
        V3dT last_vector_cache

    void WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds)
    void WindSock_t_free(WindSock_t *ws)
    V3dT WindSock_t_currentVector(WindSock_t *wind_sock)
    int WindSock_t_updateCache(WindSock_t *ws)
    V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param)

    # helpers
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
    cdef tuple _init_zero_calculation(CythonizedBaseIntegrationEngine self, const ShotProps_t *shot_props_ptr, double distance)
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
