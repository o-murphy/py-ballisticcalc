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

typedef struct {
    double cStepMultiplier;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} Config_t;

typedef struct {
    double a;
    double b;
    double c;
} CurvePoint_t;

typedef struct {
    CurvePoint_t *points;
    size_t length;
} Curve_t;

void Curve_t_free(Curve_t *curve_ptr);

typedef struct {
    double * array;
    size_t length;
} MachList_t;

//MachList_t MachList_fromArray(const double *values, size_t length);
void MachList_t_free(MachList_t *mach_list_ptr);

typedef struct {
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} Atmosphere_t;

void Atmosphere_t_updateDensityFactorAndMachForAltitude(
    const Atmosphere_t *atmo_ptr,
    double altitude,
    double *density_ratio_ptr,
    double *mach_ptr);

typedef struct {
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
} ShotProps_t;

void ShotProps_t_free(ShotProps_t *shot_props_ptr);
double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time);
int ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr);
double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach);

double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                   const Curve_t *curve_ptr,
                                   double mach);

typedef struct {
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} Wind_t;

V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr);

typedef enum {
    NONE = 0,
    ZERO_UP = 1,
    ZERO_DOWN = 2,
    ZERO = ZERO_UP | ZERO_DOWN,
    MACH = 4,
    RANGE = 8,
    APEX = 16,
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX
} TrajFlag_t;

typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajData_t;

typedef struct {
    Wind_t *winds;
    int current;
    int length;
    double next_range;
    V3dT last_vector_cache;
} WindSock_t;

void WindSock_t_free(WindSock_t *ws);
V3dT WindSock_t_currentVector(WindSock_t *wind_sock);
int WindSock_t_updateCache(WindSock_t *ws);
V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param);

typedef struct {
    int filter;
    int current_flag;
    int seen_zero;
    double time_step;
    double range_step;
    double time_of_last_record;
    double next_record_distance;
    double previous_mach;
    double previous_time;
    V3dT previous_position;
    V3dT previous_velocity;
    double previous_v_mach;
    double look_angle;
} TrajDataFilter_t;


// helpers
double getCorrection(double distance, double offset);
double calculateEnergy(double bulletWeight, double velocity);
double calculateOgw(double bulletWeight, double velocity);

#endif // TYPES_H