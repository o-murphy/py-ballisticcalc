#ifndef BINDINGS_H
#define BINDINGS_H

#include <math.h>  // For sqrt, fabs, pow, atan2, cos, sin
#include <stdio.h> // For fprintf, stderr (for error reporting)
#include <stdlib.h> // For malloc, free (needed for MachListT, CurveT, DragTable)

// Assuming v3d.h defines V3d struct
#include "v3d.h"

// --- Global Constants ---
// Declared as extern, defined in bindings.c
extern const double C_DEGREES_F_TO_R;
extern const double C_DEGREES_C_TO_K;
extern const double C_SPEED_OF_SOUND_IMPERIAL;
extern const double C_SPEED_OF_SOUND_METRIC;
extern const double C_LAPSE_RATE_K_PER_FOOT;
extern const double C_LAPSE_RATE_IMPERIAL;
extern const double C_PRESSURE_EXPONENT;
extern const double C_LOWEST_TEMP_F;
extern const double M_TO_FEET;

// --- Structure Definitions ---

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
    double a, b, c;
} CurvePointT;

typedef struct {
    CurvePointT * points;
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
    double densityFactor; // Renamed from density_ratio to match C convention and usage
    double cLowestTempC;
} AtmosphereT;

typedef struct {
    double bc;
    CurveT curve;
    MachListT machList;
    double lookAngle;
    double twist;
    double length;
    double diameter;
    double weight;
    double barrelElevation;
    double barrelAzimuth;
    double sightHeight;
    double cantCosine;
    double cantSine;
    double alt0;
    double calcStep;
    double muzzleVelocity;
    double stabilityCoefficient;
    AtmosphereT atmo;
} ShotDataT;

typedef struct {
    double CD;
    double Mach;
} DragTablePoint;

typedef struct {
    // This should likely be DragTablePoint *points, not double *points
    // because you're accessing `table->points[i].Mach` in tableToMach and calculateCurve.
    DragTablePoint * points;
    size_t length;
} DragTableT;

typedef struct {
    double velocity;
    double directionFrom;
    double untilDistance;
    double MAX_DISTANCE_FEET;
} WindT;

// --- Function Prototypes ---

// Declaration for the function that was called `update_density_factor_and_mach_for_altitude`
void updateDensityFactorAndMatchForAltitude(AtmosphereT * atmo, double altitude, double * densityRatio, double * mach);

double getCalcStepDefault(ConfigT * config);
double getCalcStep(ConfigT * config, double step);
MachListT tableToMach(DragTableT * table);
CurveT calculateCurve(DragTableT * table);
double calculateByCurveAndMachList(MachListT * machList, CurveT * curve, double mach);
double spinDrift(ShotDataT * shotData, double time);
double dragByMach(ShotDataT * shotData, double mach);
void updateStabilityCoefficient(ShotDataT * shotData);

double getCorrection(double distance, double offset);
double calculateEnergy(double bulletWeight, double velocity);
double calculateOGW(double bulletWeight, double velocity);

// Memory deallocation functions
void freeDragTable(DragTableT *table); // Needs semicolon here!
void freeCurve(CurveT * curve);       // Needs semicolon here!
void freeMachList(MachListT * machList); // Needs semicolon here!
void freeTrajectory(ShotDataT * shotData); // Needs semicolon here!

V3d windToVector(const WindT *w);

#endif // BINDINGS_H