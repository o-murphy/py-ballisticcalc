# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT


cdef extern from "include/bind.h" nogil:
    MachList_t MachList_t_fromPylist(PyObject *pylist)
    Curve_t Curve_t_fromPylist(PyObject *data_points)


# Declare the C header file
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

    # Declare the V3dT structure
    ctypedef struct Config_t:
        double cStepMultiplier
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

    Config_t Config_t_fromPyObject(PyObject * config)

    ctypedef struct CurvePoint_t:
        double a, b, c

    ctypedef struct Curve_t:
        CurvePoint_t * points
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
        double *mach_ptr
    )

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

    void ShotData_t_free(ShotData_t *shot_data_ptr)
    double ShotData_t_spinDrift(const ShotData_t *shot_data_ptr, double time)
    int ShotData_t_updateStabilityCoefficient(ShotData_t *shot_data_ptr)
    double ShotData_t_dragByMach(const ShotData_t *shot_data_ptr, double mach)
    double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                       const Curve_t *curve_ptr,
                                       double mach)

    ctypedef struct Wind_t:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr)
    # Wind_t Wind_t_fromPythonObj(PyObject *w)


# python to C objects conversion
cdef Config_t Config_t_from_pyobject(object config)

cdef MachList_t MachList_t_from_pylist(list[object] data)
cdef Curve_t Curve_t_from_pylist(list[object] data_points)

cdef Wind_t Wind_t_from_python(object w)
