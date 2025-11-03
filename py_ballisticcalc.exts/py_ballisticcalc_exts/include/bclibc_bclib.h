#ifndef BCLIBC_BCLIB_H
#define BCLIBC_BCLIB_H

#include "bclibc_v3d.h"
#include "bclibc_log.h"
#include "bclibc_error_stack.h"
#include <stddef.h>

extern const double cDegreesFtoR;
extern const double cDegreesCtoK;
extern const double cSpeedOfSoundImperial;
extern const double cSpeedOfSoundMetric;
extern const double cLapseRateKperFoot;
extern const double cLapseRateImperial;
extern const double cPressureExponent;
extern const double cLowestTempF;
extern const double mToFeet;

extern const double cMaxWindDistanceFeet;
extern const double cEarthAngularVelocityRadS;

typedef struct
{
    double cStepMultiplier;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} Config_t;

typedef struct
{
    double a;
    double b;
    double c;
    double d; // PCHIP cubic constant term for segment (y at left knot)
} CurvePoint_t;

typedef struct
{
    CurvePoint_t *points;
    size_t length;
} Curve_t;

typedef struct
{
    double *array;
    size_t length;
} MachList_t;

typedef struct
{
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} Atmosphere_t;

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
} Coriolis_t;

typedef struct
{
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} Wind_t;

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
    Wind_t *winds;
    int current;
    int length;
    double next_range;
    BCLIBC_V3dT last_vector_cache;
} WindSock_t;

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
    Curve_t curve;
    MachList_t mach_list;
    Atmosphere_t atmo;
    Coriolis_t coriolis;
    WindSock_t wind_sock;
    BCLIBC_TrajFlag filter_flags;
} ShotProps_t;

/**
 * Keys used to look up specific values within a BCLIBC_BaseTraj struct.
 */
typedef enum
{
    KEY_TIME,
    KEY_MACH,
    KEY_POS_X,
    KEY_POS_Y,
    KEY_POS_Z,
    KEY_VEL_X,
    KEY_VEL_Y,
    KEY_VEL_Z
} InterpKey;

#ifdef __cplusplus
extern "C"
{
#endif

    void Curve_t_release(Curve_t *curve_ptr);

    // MachList_t MachList_fromArray(const double *values, size_t length);
    void MachList_t_release(MachList_t *mach_list_ptr);

    void Atmosphere_t_updateDensityFactorAndMachForAltitude(
        const Atmosphere_t *atmo_ptr,
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr);

    void ShotProps_t_release(ShotProps_t *shot_props_ptr);
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time);
    BCLIBC_ErrorType ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr);
    double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach);

    BCLIBC_ErrorType WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds);
    void WindSock_t_release(WindSock_t *ws);
    BCLIBC_V3dT WindSock_t_currentVector(const WindSock_t *wind_sock);
    BCLIBC_ErrorType WindSock_t_updateCache(WindSock_t *ws);
    BCLIBC_V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param);

    // helpers
    double getCorrection(double distance, double offset);
    double calculateEnergy(double bulletWeight, double velocity);
    double calculateOgw(double bulletWeight, double velocity);

    void Coriolis_t_coriolis_acceleration_local(
        const Coriolis_t *coriolis_ptr,
        const BCLIBC_V3dT *velocity_ptr,
        BCLIBC_V3dT *accel_ptr);

    BCLIBC_ErrorType BCLIBC_BaseTrajData_interpolate(
        InterpKey key_kind,
        double key_value,
        const BCLIBC_BaseTrajData *p0,
        const BCLIBC_BaseTrajData *p1,
        const BCLIBC_BaseTrajData *p2,
        BCLIBC_BaseTrajData *out);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_BCLIB_H
