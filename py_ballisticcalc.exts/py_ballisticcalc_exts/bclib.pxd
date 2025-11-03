# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.error_stack cimport BCLIBC_ErrorType


cdef extern from "include/bclibc_bclib.h" nogil:
    ctypedef enum BCLIBC_LogLevel:
        BCLIBC_LOG_LEVEL_CRITICAL,
        BCLIBC_LOG_LEVEL_ERROR,
        BCLIBC_LOG_LEVEL_WARNING,
        BCLIBC_LOG_LEVEL_INFO,
        BCLIBC_LOG_LEVEL_DEBUG,
        BCLIBC_LOG_LEVEL_NOTSET

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

    void Curve_t_release(Curve_t *curve_ptr) noexcept nogil

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
        BCLIBC_V3dT *velocity_ptr,
        BCLIBC_V3dT *accel_ptr
    ) noexcept nogil

    ctypedef struct Wind_t:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

    ctypedef struct WindSock_t:
        Wind_t *winds
        int current
        int length
        double next_range
        BCLIBC_V3dT last_vector_cache

    BCLIBC_ErrorType WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds) noexcept nogil
    void WindSock_t_release(WindSock_t *ws) noexcept nogil
    BCLIBC_V3dT WindSock_t_currentVector(WindSock_t *wind_sock) noexcept nogil
    BCLIBC_ErrorType WindSock_t_updateCache(WindSock_t *ws) noexcept nogil
    BCLIBC_V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param) noexcept nogil

    ctypedef enum BCLIBC_TrajFlag:
        BCLIBC_TRAJ_FLAG_NONE = 0,
        BCLIBC_TRAJ_FLAG_ZERO_UP = 1,
        BCLIBC_TRAJ_FLAG_ZERO_DOWN = 2,
        BCLIBC_TRAJ_FLAG_ZERO = BCLIBC_TRAJ_FLAG_ZERO_UP | BCLIBC_TRAJ_FLAG_ZERO_DOWN,
        BCLIBC_TRAJ_FLAG_MACH = 4,
        BCLIBC_TRAJ_FLAG_RANGE = 8,
        BCLIBC_TRAJ_FLAG_APEX = 16,
        BCLIBC_TRAJ_FLAG_ALL = BCLIBC_TRAJ_FLAG_RANGE | BCLIBC_TRAJ_FLAG_ZERO_UP | BCLIBC_TRAJ_FLAG_ZERO_DOWN | BCLIBC_TRAJ_FLAG_MACH | BCLIBC_TRAJ_FLAG_APEX
        BCLIBC_TRAJ_FLAG_MRT = 32

    ctypedef struct BCLIBC_BaseTrajData:
        double time
        BCLIBC_V3dT position
        BCLIBC_V3dT velocity
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
        BCLIBC_TrajFlag filter_flags

    void ShotProps_t_release(ShotProps_t *shot_props_ptr) noexcept nogil
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time) noexcept nogil
    BCLIBC_ErrorType ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr) noexcept nogil
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

    BCLIBC_ErrorType BCLIBC_BaseTrajData_interpolate(
        InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData *p0,
        const BCLIBC_BaseTrajData *p1,
        const BCLIBC_BaseTrajData *p2,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil
