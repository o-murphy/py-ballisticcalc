#ifndef BCLIBC_BCLIB_H
#define BCLIBC_BCLIB_H

#include "bclibc_v3d.h"
#include "bclibc_log.h"
#include "bclibc_error_stack.h"
#include <stddef.h>

extern const double BCLIBC_cDegreesFtoR;
extern const double BCLIBC_cDegreesCtoK;
extern const double BCLIBC_cSpeedOfSoundImperial;
extern const double BCLIBC_cSpeedOfSoundMetric;
extern const double BCLIBC_cLapseRateKperFoot;
extern const double BCLIBC_cLapseRateImperial;
extern const double BCLIBC_cPressureExponent;
extern const double BCLIBC_cLowestTempF;
extern const double BCLIBC_mToFeet;

extern const double BCLIBC_cMaxWindDistanceFeet;
extern const double BCLIBC_cEarthAngularVelocityRadS;

typedef struct
{
    double cStepMultiplier;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} BCLIBC_Config;

typedef struct
{
    double a;
    double b;
    double c;
    double d; // PCHIP cubic constant term for segment (y at left knot)
} BCLIBC_CurvePoint;

typedef struct
{
    BCLIBC_CurvePoint *points;
    size_t length;
} BCLIBC_Curve;

typedef struct
{
    double *array;
    size_t length;
} BCLIBC_MachList;

typedef struct
{
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} BCLIBC_Atmosphere;

typedef struct
{
    double sin_lat;
    double cos_lat;
    double sin_az;
    double cos_az;
    double range_east;
    double range_north;
    double cross_east;
    double cross_north;
    int flat_fire_only;
    double muzzle_velocity_fps;
} BCLIBC_Coriolis;

typedef struct
{
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} BCLIBC_Wind;

typedef enum
{
    BCLIBC_TRAJ_FLAG_NONE = 0,
    BCLIBC_TRAJ_FLAG_ZERO_UP = 1,
    BCLIBC_TRAJ_FLAG_ZERO_DOWN = 2,
    BCLIBC_TRAJ_FLAG_ZERO = BCLIBC_TRAJ_FLAG_ZERO_UP | BCLIBC_TRAJ_FLAG_ZERO_DOWN,
    BCLIBC_TRAJ_FLAG_MACH = 4,
    BCLIBC_TRAJ_FLAG_RANGE = 8,
    BCLIBC_TRAJ_FLAG_APEX = 16,
    BCLIBC_TRAJ_FLAG_ALL = BCLIBC_TRAJ_FLAG_RANGE | BCLIBC_TRAJ_FLAG_ZERO_UP | BCLIBC_TRAJ_FLAG_ZERO_DOWN | BCLIBC_TRAJ_FLAG_MACH | BCLIBC_TRAJ_FLAG_APEX,
    BCLIBC_TRAJ_FLAG_MRT = 32
} BCLIBC_TrajFlag;

typedef struct
{
    double time;
    BCLIBC_V3dT position;
    BCLIBC_V3dT velocity;
    double mach;
} BCLIBC_BaseTrajData;

typedef struct
{
    BCLIBC_Wind *winds;
    int current;
    int length;
    double next_range;
    BCLIBC_V3dT last_vector_cache;
} BCLIBC_WindSock;

typedef struct
{
    double bc;
    double look_angle;
    double twist;
    double length;
    double diameter;
    double weight;
    double barrel_elevation;
    double barrel_azimuth;
    double sight_height;
    double cant_cosine;
    double cant_sine;
    double alt0;
    double calc_step;
    double muzzle_velocity;
    double stability_coefficient;
    BCLIBC_Curve curve;
    BCLIBC_MachList mach_list;
    BCLIBC_Atmosphere atmo;
    BCLIBC_Coriolis coriolis;
    BCLIBC_WindSock wind_sock;
    BCLIBC_TrajFlag filter_flags;
} BCLIBC_ShotProps;

/**
 * Keys used to look up specific values within a BCLIBC_BaseTraj struct.
 */
typedef enum
{
    BCLIBC_BASE_TRAJ_INTERP_KEY_TIME,
    BCLIBC_BASE_TRAJ_INTERP_KEY_MACH,
    BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X,
    BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y,
    BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z,
    BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X,
    BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y,
    BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z,
} BCLIBC_BaseTrajSeq_InterpKey;

#ifdef __cplusplus
#define restrict
#endif

#ifdef __cplusplus
#define restrict
#endif

#ifdef __cplusplus
extern "C"
{
#endif

    void BCLIBC_Curve_release(BCLIBC_Curve *curve_ptr);

    // BCLIBC_MachList MachList_fromArray(const double *values, size_t length);
    void BCLIBC_MachList_release(BCLIBC_MachList *mach_list_ptr);

    void BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude(
        const BCLIBC_Atmosphere *restrict atmo_ptr,
        double altitude,
        double *restrict density_ratio_ptr,
        double *restrict mach_ptr);

    void BCLIBC_ShotProps_release(BCLIBC_ShotProps *shot_props_ptr);
    double BCLIBC_ShotProps_spinDrift(const BCLIBC_ShotProps *shot_props_ptr, double time);
    BCLIBC_ErrorType BCLIBC_ShotProps_updateStabilityCoefficient(BCLIBC_ShotProps *shot_props_ptr);
    double BCLIBC_ShotProps_dragByMach(const BCLIBC_ShotProps *shot_props_ptr, double mach);

    BCLIBC_ErrorType BCLIBC_WindSock_init(BCLIBC_WindSock *ws, size_t length, BCLIBC_Wind *winds);
    void BCLIBC_WindSock_release(BCLIBC_WindSock *ws);
    BCLIBC_V3dT BCLIBC_WindSock_currentVector(const BCLIBC_WindSock *wind_sock);
    BCLIBC_ErrorType BCLIBC_WindSock_updateCache(BCLIBC_WindSock *ws);
    BCLIBC_V3dT BCLIBC_WindSock_vectorForRange(BCLIBC_WindSock *ws, double next_range_param);

    BCLIBC_V3dT BCLIBC_adjustRangeFromCoriolis(const BCLIBC_Coriolis *coriolis, double time, const BCLIBC_V3dT *range_vector);
    void BCLIBC_Coriolis_coriolisAccelerationLocal(
        const BCLIBC_Coriolis *restrict coriolis_ptr,
        const BCLIBC_V3dT *restrict velocity_ptr,
        BCLIBC_V3dT *restrict accel_ptr);

    // helpers
    double BCLIBC_getCorrection(double distance, double offset);
    double BCLIBC_calculateEnergy(double bulletWeight, double velocity);
    double BCLIBC_calculateOgw(double bulletWeight, double velocity);

    void BCLIBC_Coriolis_flatFireOffsets(const BCLIBC_Coriolis *coriolis, double time, double distance_ft, double drop_ft, double *delta_y, double *delta_z);
    BCLIBC_V3dT BCLIBC_Coriolis_adjustRange(const BCLIBC_Coriolis *coriolis, double time, const BCLIBC_V3dT *range_vector);

    BCLIBC_ErrorType BCLIBC_BaseTrajData_interpolate(
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData *restrict p0,
        const BCLIBC_BaseTrajData *restrict p1,
        const BCLIBC_BaseTrajData *restrict p2,
        BCLIBC_BaseTrajData *restrict out);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_BCLIB_H
