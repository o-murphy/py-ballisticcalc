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
} ConfigT;

typedef struct {
    double a;
    double b;
    double c;
} CurvePointT;

typedef struct {
    CurvePointT *points;
    size_t length;
} CurveT;

typedef struct {
    double * array;
    size_t length;
} MachListT;

typedef struct {
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} AtmosphereT;

typedef struct {
    double bc;
    CurveT curve;
    MachListT mach_list;
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
    AtmosphereT atmo;
} ShotDataT;

typedef struct {
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} WindT;

#endif // TYPES_H