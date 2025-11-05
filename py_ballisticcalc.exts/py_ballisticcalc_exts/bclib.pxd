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

    cdef const double BCLIBC_cDegreesFtoR
    cdef const double BCLIBC_cDegreesCtoK
    cdef const double BCLIBC_cSpeedOfSoundImperial
    cdef const double BCLIBC_cSpeedOfSoundMetric
    cdef const double BCLIBC_cLapseRateKperFoot
    cdef const double BCLIBC_cLapseRateImperial
    cdef const double BCLIBC_cPressureExponent
    cdef const double BCLIBC_cLowestTempF
    cdef const double BCLIBC_mToFeet
    cdef const double BCLIBC_cMaxWindDistanceFeet

    ctypedef struct BCLIBC_Config:
        double cStepMultiplier
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

    ctypedef struct BCLIBC_CurvePoint:
        double a, b, c, d

    ctypedef struct BCLIBC_Curve:
        BCLIBC_CurvePoint * points
        size_t length

    void BCLIBC_Curve_release(BCLIBC_Curve *curve_ptr) noexcept nogil

    ctypedef struct BCLIBC_MachList:
        double * array
        size_t length

    void BCLIBC_MachList_release(BCLIBC_MachList *mach_list_ptr) noexcept nogil

    ctypedef struct BCLIBC_Atmosphere:
        double _t0
        double _a0
        double _p0
        double _mach
        double density_ratio
        double cLowestTempC

    void BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
        const BCLIBC_Atmosphere *atmo_ptr,
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr
    ) noexcept nogil

    ctypedef struct BCLIBC_Coriolis:
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

    void BCLIBC_Coriolis_coriolisAccelerationLocal(
        const BCLIBC_Coriolis *coriolis_ptr,
        BCLIBC_V3dT *velocity_ptr,
        BCLIBC_V3dT *accel_ptr
    ) noexcept nogil

    ctypedef struct BCLIBC_Wind:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

    ctypedef struct BCLIBC_WindSock:
        BCLIBC_Wind *winds
        int current
        int length
        double next_range
        BCLIBC_V3dT last_vector_cache

    BCLIBC_ErrorType BCLIBC_WindSock_init(BCLIBC_WindSock *ws, size_t length, BCLIBC_Wind *winds) noexcept nogil
    void BCLIBC_WindSock_release(BCLIBC_WindSock *ws) noexcept nogil
    BCLIBC_V3dT BCLIBC_WindSock_currentVector(BCLIBC_WindSock *wind_sock) noexcept nogil
    BCLIBC_ErrorType BCLIBC_WindSock_updateCache(BCLIBC_WindSock *ws) noexcept nogil
    BCLIBC_V3dT BCLIBC_WindSock_vectorForRange(BCLIBC_WindSock *ws, double next_range_param) noexcept nogil

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

    ctypedef struct BCLIBC_ShotProps:
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
        BCLIBC_Curve curve
        BCLIBC_MachList mach_list
        BCLIBC_Atmosphere atmo
        BCLIBC_Coriolis coriolis
        BCLIBC_WindSock wind_sock
        BCLIBC_TrajFlag filter_flags

    void BCLIBC_ShotProps_release(BCLIBC_ShotProps *shot_props_ptr) noexcept nogil
    double BCLIBC_ShotProps_spinDrift(
        const BCLIBC_ShotProps *shot_props_ptr, double time
    ) noexcept nogil
    BCLIBC_ErrorType BCLIBC_ShotProps_updateStabilityCoefficient(
        BCLIBC_ShotProps *shot_props_ptr
    ) noexcept nogil
    double BCLIBC_ShotProps_dragByMach(
        const BCLIBC_ShotProps *shot_props_ptr, double mach
    ) noexcept nogil

    ctypedef enum BCLIBC_BaseTrajSeq_InterpKey:
        BCLIBC_BASE_TRAJ_INTERP_KEY_TIME
        BCLIBC_BASE_TRAJ_INTERP_KEY_MACH
        BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X
        BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y
        BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z
        BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X
        BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y
        BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z

    # helpers
    double BCLIBC_getCorrection(double distance, double offset) noexcept nogil
    double BCLIBC_calculateEnergy(double bulletWeight, double velocity) noexcept nogil
    double BCLIBC_calculateOgw(double bulletWeight, double velocity) noexcept nogil

    BCLIBC_ErrorType BCLIBC_BaseTrajData_interpolate(
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData *p0,
        const BCLIBC_BaseTrajData *p1,
        const BCLIBC_BaseTrajData *p2,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil
