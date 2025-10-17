#ifndef TYPES_H
#define TYPES_H

#include "v3d.h"
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
    double bc;
    Curve_t curve;
    MachList_t mach_list;
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
    int filter_flags;
    Atmosphere_t atmo;
    Coriolis_t coriolis;
} ShotProps_t;

typedef struct
{
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} Wind_t;

typedef enum
{
    TFLAG_NONE = 0,
    TFLAG_ZERO_UP = 1,
    TFLAG_ZERO_DOWN = 2,
    TFLAG_ZERO = TFLAG_ZERO_UP | TFLAG_ZERO_DOWN,
    TFLAG_MACH = 4,
    TFLAG_RANGE = 8,
    TFLAG_APEX = 16,
    TFLAG_ALL = TFLAG_RANGE | TFLAG_ZERO_UP | TFLAG_ZERO_DOWN | TFLAG_MACH | TFLAG_APEX,
    TFLAG_MRT = 32
} TrajFlag_t;

typedef struct
{
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajData_t;

typedef struct
{
    Wind_t *winds;
    int current;
    int length;
    double next_range;
    V3dT last_vector_cache;
} WindSock_t;

typedef enum
{
    NoRangeError,
    RangeErrorInvalidParameter,
    RangeErrorMinimumVelocityReached,
    RangeErrorMaximumDropReached,
    RangeErrorMinimumAltitudeReached,
} TerminationReason;

#ifdef __cplusplus
extern "C"
{
#endif

    void Curve_t_free(Curve_t *curve_ptr);

    // MachList_t MachList_fromArray(const double *values, size_t length);
    void MachList_t_free(MachList_t *mach_list_ptr);

    void Atmosphere_t_updateDensityFactorAndMachForAltitude(
        const Atmosphere_t *atmo_ptr,
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr);

    void ShotProps_t_freeResources(ShotProps_t *shot_props_ptr);
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time);
    int ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr);
    double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach);

    double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                       const Curve_t *curve_ptr,
                                       double mach);

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr);

    BaseTrajData_t *BaseTrajData_t_create(double time, V3dT position, V3dT velocity, double mach);
    void BaseTrajData_t_destroy(BaseTrajData_t *ptr);

    void WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds);
    void WindSock_t_freeResources(WindSock_t *ws);
    V3dT WindSock_t_currentVector(const WindSock_t *wind_sock);
    int WindSock_t_updateCache(WindSock_t *ws);
    V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param);

    // helpers
    double getCorrection(double distance, double offset);
    double calculateEnergy(double bulletWeight, double velocity);
    double calculateOgw(double bulletWeight, double velocity);

    void Coriolis_t_coriolis_acceleration_local(
        const Coriolis_t *coriolis_ptr,
        const V3dT *velocity_ptr,
        V3dT *accel_ptr);

#ifdef __cplusplus
}
#endif

#endif // TYPES_H
