#ifndef TYPES_H
#define TYPES_H

//#include "v3d.h"


typedef struct {
    double cMaxCalcStepSizeFeet;
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

typedef struct {
    double * array;
    size_t length;
} MachList_t;

typedef struct {
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} Atmosphere_t;

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
    Atmosphere_t atmo;
} ShotData_t;

typedef struct {
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} Wind_t;

#endif // TYPES_H