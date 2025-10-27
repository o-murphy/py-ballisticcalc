# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT


cdef extern from "include/bclib.h" nogil:
    ctypedef enum LogLevel:
        LOG_LEVEL_CRITICAL,
        LOG_LEVEL_ERROR,
        LOG_LEVEL_WARNING,
        LOG_LEVEL_INFO,
        LOG_LEVEL_DEBUG,
        LOG_LEVEL_NOTSET

    void setLogLevel(LogLevel level) noexcept nogil
    void initLogLevel()

    cdef const double cDegreesFtoR
    cdef const double cDegreesCtoK
    cdef const double cSpeedOfSoundImperial
    cdef const double cSpeedOfSoundMetric
    cdef const double cLapseRateKperFoot
    cdef const double cLapseRateImperial
    cdef const double cPressureExponent
    cdef const double cLowestTempF
    cdef const double mToFeet
    cdef const double cMaxWindDistanceFeet

    ctypedef enum ErrorCode:
        # General error codes
        NO_ERROR
        ZERO_DIVISION_ERROR
        VALUE_ERROR
        KEY_ERROR
        INDEX_ERROR
        MEMORY_ERROR
        ARITHMETIC_ERROR
        INPUT_ERROR
        RUNTIME_ERROR

        # Solver specific, not real errors, just termination reasons!
        RANGE_ERROR
        RANGE_ERROR_MINIMUM_VELOCITY_REACHED
        RANGE_ERROR_MAXIMUM_DROP_REACHED
        RANGE_ERROR_MINIMUM_ALTITUDE_REACHED

        OUT_OF_RANGE_ERROR

        ZERO_FINDING_ERROR

        UNDEFINED_ERROR

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

    void Curve_t_release(Curve_t *curve_ptr)

    ctypedef struct MachList_t:
        double * array
        size_t length

    void MachList_t_release(MachList_t *mach_list_ptr) noexcept nogil

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

    void Coriolis_t_coriolis_acceleration_local(
        const Coriolis_t *coriolis_ptr,
        V3dT *velocity_ptr,
        V3dT *accel_ptr
    ) noexcept nogil

    double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                       const Curve_t *curve_ptr,
                                       double mach) noexcept nogil

    ctypedef struct Wind_t:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr) noexcept nogil

    ctypedef struct WindSock_t:
        Wind_t *winds
        int current
        int length
        double next_range
        V3dT last_vector_cache

    ErrorCode WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds) noexcept nogil
    void WindSock_t_release(WindSock_t *ws) noexcept nogil
    V3dT WindSock_t_currentVector(WindSock_t *wind_sock) noexcept nogil
    ErrorCode WindSock_t_updateCache(WindSock_t *ws) noexcept nogil
    V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param) noexcept nogil

    ctypedef enum TrajFlag_t:
        TFLAG_NONE = 0,
        TFLAG_ZERO_UP = 1,
        TFLAG_ZERO_DOWN = 2,
        TFLAG_ZERO = TFLAG_ZERO_UP | TFLAG_ZERO_DOWN,
        TFLAG_MACH = 4,
        TFLAG_RANGE = 8,
        TFLAG_APEX = 16,
        TFLAG_ALL = TFLAG_RANGE | TFLAG_ZERO_UP | TFLAG_ZERO_DOWN | TFLAG_MACH | TFLAG_APEX
        TFLAG_MRT = 32

    ctypedef struct BaseTrajData_t:
        double time
        V3dT position
        V3dT velocity
        double mach

    ctypedef struct ShotProps_t:
        double bc
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
        Curve_t curve
        MachList_t mach_list
        Atmosphere_t atmo
        Coriolis_t coriolis
        WindSock_t wind_sock
        TrajFlag_t filter_flags

    void ShotProps_t_release(ShotProps_t *shot_props_ptr) noexcept nogil
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time) noexcept nogil
    ErrorCode ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr) noexcept nogil
    double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach) noexcept nogil

    ctypedef enum InterpKey:
        KEY_TIME
        KEY_MACH
        KEY_POS_X
        KEY_POS_Y
        KEY_POS_Z
        KEY_VEL_X
        KEY_VEL_Y
        KEY_VEL_Z

    # helpers
    double getCorrection(double distance, double offset) noexcept nogil
    double calculateEnergy(double bulletWeight, double velocity) noexcept nogil
    double calculateOgw(double bulletWeight, double velocity) noexcept nogil

    ErrorCode BaseTrajData_t_interpolate(
        InterpKey key_kind,
        double key_value,
        const BaseTrajData_t *p0,
        const BaseTrajData_t *p1,
        const BaseTrajData_t *p2,
        BaseTrajData_t *out
    ) noexcept nogil
