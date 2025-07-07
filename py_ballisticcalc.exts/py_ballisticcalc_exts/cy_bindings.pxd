# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)

# Declare the C header file
cdef extern from "include/types.h" nogil:
    # Declare the V3dT structure
    ctypedef struct Config_t:
        double cMaxCalcStepSizeFeet
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

    ctypedef struct CurvePoint_t:
        double a, b, c

    ctypedef struct Curve_t:
        CurvePoint_t * points
        size_t length

    ctypedef struct MachList_t:
        double * array
        size_t length

    ctypedef struct Atmosphere_t:
        double _t0
        double _a0
        double _p0
        double _mach
        double density_ratio
        double cLowestTempC

    ctypedef struct ShotData_t:
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
        Atmosphere_t atmo

    ctypedef struct Wind_t:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET


cdef Config_t config_bind(object config)

cdef void update_density_factor_and_mach_for_altitude(
    const Atmosphere_t * atmo_ptr, double altitude, double * density_ratio_ptr, double * mach_ptr
)

cdef double cy_get_calc_step(const Config_t * config_ptr, double step = ?)
cdef MachList_t cy_table_to_mach(list[object] data)
cdef Curve_t cy_calculate_curve(list[object] data_points)
cdef double cy_calculate_by_curve_and_mach_list(const MachList_t *mach_list_ptr, const Curve_t *curve_ptr, double mach)
cdef double cy_spin_drift(const ShotData_t * shot_data_ptr, double time)
cdef double cy_drag_by_mach(const ShotData_t * shot_data_ptr, double mach)
cdef void cy_update_stability_coefficient(ShotData_t * shot_data_ptr)

cdef void free_curve(Curve_t *curve_ptr)
cdef void free_mach_list(MachList_t *mach_list_ptr)
cdef void free_trajectory(ShotData_t *shot_data_ptr)

cdef double cDegreesFtoR
cdef double cSpeedOfSoundImperial
cdef double cLapseRateImperial

cdef Wind_t WindT_from_python(object w)
cdef V3dT WindT_to_V3dT(const Wind_t * wind_ptr)