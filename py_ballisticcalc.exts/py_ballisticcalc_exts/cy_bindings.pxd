# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT


cdef extern from "include/bind.h" nogil:
    MachList_t MachList_t_fromPylist(const PyObject *pylist) noexcept nogil
    Curve_t Curve_t_fromPylist(const PyObject *data_points) noexcept nogil
    Config_t Config_t_fromPyObject(const PyObject * config) noexcept nogil
    Wind_t Wind_t_fromPyObject(PyObject *w) noexcept nogil


cdef extern from "include/bclib.h" nogil:
    cdef const double cDegreesFtoR
    cdef const double cDegreesCtoK
    cdef const double cSpeedOfSoundImperial
    cdef const double cSpeedOfSoundMetric
    cdef const double cLapseRateKperFoot
    cdef const double cLapseRateImperial
    cdef const double cPressureExponent
    cdef const double cLowestTempF
    cdef const double mToFeet

    ctypedef struct Config_t:
        double cStepMultiplier
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

    ctypedef struct CurvePoint_t:
        double a, b, c, d

    ctypedef struct Curve_t:
        CurvePoint_t * points
        size_t length

    void Curve_t_free(Curve_t *curve_ptr)

    ctypedef struct MachList_t:
        double * array
        size_t length

    void MachList_t_free(MachList_t *mach_list_ptr) noexcept nogil

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
        double *mach_ptr
    ) noexcept nogil

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

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr) noexcept nogil

    void Coriolis_t_coriolis_acceleration_local(
        const Coriolis_t *coriolis_ptr,
        V3dT *velocity_ptr,
        V3dT *accel_ptr
    ) noexcept nogil


# python to C objects conversion
cdef Config_t Config_t_from_pyobject(object config)
cdef MachList_t MachList_t_from_pylist(list[object] data)
cdef Curve_t Curve_t_from_pylist(list[object] data_points)
cdef Wind_t Wind_t_from_py(object w)
