from libcpp.vector cimport vector
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT


cdef extern from "include/bclibc/base_types.hpp" namespace "bclibc" nogil:
    cdef enum class BCLIBC_LogLevel:
        CRITICAL,
        ERROR,
        WARNING,
        INFO,
        DEBUG,
        NOTSET

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

    cdef cppclass BCLIBC_Config:
        double cStepMultiplier
        double cZeroFindingAccuracy
        double cMinimumVelocity
        double cMaximumDrop
        int cMaxIterations
        double cGravityConstant
        double cMinimumAltitude

        BCLIBC_Config() except +
        BCLIBC_Config(
            double cStepMultiplier,
            double cZeroFindingAccuracy,
            double cMinimumVelocity,
            double cMaximumDrop,
            int cMaxIterations,
            double cGravityConstant,
            double cMinimumAltitude
        ) except +

    cdef cppclass BCLIBC_CurvePoint:
        double a, b, c, d

        BCLIBC_CurvePoint() except +
        BCLIBC_CurvePoint(
            double a,
            double b,
            double c,
            double d
        ) except +

    ctypedef vector[BCLIBC_CurvePoint] BCLIBC_Curve
    ctypedef vector[double] BCLIBC_MachList

    cdef cppclass BCLIBC_Atmosphere:
        double _t0
        double _a0
        double _p0
        double _mach
        double density_ratio
        double cLowestTempC

        BCLIBC_Atmosphere() except +
        BCLIBC_Atmosphere(
            double _t0,
            double _a0,
            double _p0,
            double _mach,
            double density_ratio,
            double cLowestTempC
        ) except +

        void update_density_factor_and_mach_for_altitude(
            double altitude,
            double &density_ratio_out,
            double &mach_out
        ) const

    cdef cppclass BCLIBC_Coriolis:
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

        BCLIBC_Coriolis() except +

        BCLIBC_Coriolis(
            double sin_lat,
            double cos_lat,
            double sin_az,
            double cos_az,
            double range_east,
            double range_north,
            double cross_east,
            double cross_north,
            int flat_fire_only,
            double muzzle_velocity_fps
        ) except +

        void flat_fire_offsets(
            double time,
            double distance_ft,
            double drop_ft,
            double &delta_y,
            double &delta_z
        ) const

        BCLIBC_V3dT adjust_range(
            double time, const BCLIBC_V3dT &range_vector
        ) const

        void coriolis_acceleration_local(
            const BCLIBC_V3dT &velocity_vector,
            BCLIBC_V3dT &accel_out
        ) const

    cdef cppclass BCLIBC_Wind:
        double velocity
        double direction_from
        double until_distance
        double MAX_DISTANCE_FEET

        BCLIBC_Wind() except +

        BCLIBC_Wind(
            double velocity,
            double direction_from,
            double until_distance,
            double MAX_DISTANCE_FEET
        ) except +

        BCLIBC_V3dT as_V3dT() const

    cdef cppclass BCLIBC_WindSock:
        vector[BCLIBC_Wind] winds
        int current
        double next_range
        BCLIBC_V3dT last_vector_cache

        BCLIBC_WindSock() except +
        BCLIBC_WindSock(vector[BCLIBC_Wind] winds_vec) except+
        void push(const BCLIBC_Wind &wind) except +
        void update_cache() except +
        BCLIBC_V3dT current_vector() const
        BCLIBC_V3dT vector_for_range(double next_range_param) except +

    cdef enum class BCLIBC_TerminationReason:
        # Solver specific, not real errors, just termination reasons!
        NO_TERMINATE
        TARGET_RANGE_REACHED
        MINIMUM_VELOCITY_REACHED
        MAXIMUM_DROP_REACHED
        MINIMUM_ALTITUDE_REACHED
        # Special flag to terminate integration via handler's request
        HANDLER_REQUESTED_STOP

    cdef enum BCLIBC_TrajFlag:
        BCLIBC_TRAJ_FLAG_NONE
        BCLIBC_TRAJ_FLAG_ZERO_UP
        BCLIBC_TRAJ_FLAG_ZERO_DOWN
        BCLIBC_TRAJ_FLAG_ZERO
        BCLIBC_TRAJ_FLAG_MACH
        BCLIBC_TRAJ_FLAG_RANGE
        BCLIBC_TRAJ_FLAG_APEX
        BCLIBC_TRAJ_FLAG_ALL
        BCLIBC_TRAJ_FLAG_MRT

    cdef cppclass BCLIBC_ShotProps:
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

        BCLIBC_ShotProps() except +

        BCLIBC_ShotProps(
            double bc,
            double look_angle,
            double twist,
            double length,
            double diameter,
            double weight,
            double barrel_elevation,
            double barrel_azimuth,
            double sight_height,
            double cant_cosine,
            double cant_sine,
            double alt0,
            double calc_step,
            double muzzle_velocity,
            double stability_coefficient,
            BCLIBC_Curve curve,
            BCLIBC_MachList mach_list,
            BCLIBC_Atmosphere atmo,
            BCLIBC_Coriolis coriolis,
            BCLIBC_WindSock wind_sock,
            BCLIBC_TrajFlag filter_flags) except +

        void update_stability_coefficient() except +ZeroDivisionError
        double spin_drift(double time) const
        double drag_by_mach(double mach) except +ValueError

    # helpers
    double BCLIBC_getCorrection(double distance, double offset) noexcept nogil
    double BCLIBC_calculateEnergy(double bulletWeight, double velocity) noexcept nogil
    double BCLIBC_calculateOgw(double bulletWeight, double velocity) noexcept nogil
