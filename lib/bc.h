#ifndef BC_H
#define BC_H

#include <stdbool.h>
#include "v3d.h"
#include "tData.h"
#include "tDataFilter.h"
#include "wind.h"
#include "drag.h"
#include "atmo.h"
#include "config.h"

typedef enum{
    SUCCESS = 0,
    ERROR_NULL_ENGINE = -1,
    ERROR_NULL_SHOTDATA = -2,
    ERROR_NULL_ZEROANGLE = -3,
    ERROE_NULL_TRAJECTORY = -4,
    ERROR_INVALID_SHOTDATA = -5,

    ERROR_MALLOC_FAILED = -6,
    ERROR_REALLOC_FAILED = -7,

    ERROR_INTEGRATE_FAILED = -8,
    ERROR_NULL_ZEROANGLE_OUT = -9,
    MIN_VELOCITY_REACHED = 1,
    MAX_DROP_REACHED = 2,
    MIN_ALTITUDE_REACHED = 3,
    MAX_ITERATIONS_REACHED = 4
} CalculationStatus;

// double getCalcStepDefault(ConfigT * config);
// double getCalcStep(ConfigT * config, double step);

typedef struct
{
    double bc;
    DragTableT *dragTable;
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
    AtmosphereT *atmo;
    WindsT *winds;
} ShotDataT;

double spinDrift(ShotDataT *shotData, double time);
double dragByMach(ShotDataT *shotData, double mach);
void updateStabilityCoefficient(ShotDataT *shotData);

typedef struct
{
    ShotDataT *shotData;
    CurveT curve;
    MachListT machList;
    TrajectoryDataFilterT dataFilter;
    WindSockT windSock;
} TrajectoryPropsT;

typedef struct
{
    ConfigT *config;
    V3dT gravityVector;
    TrajectoryPropsT tProps;
} EngineT;

int initEngine(EngineT *engine, ConfigT *config);
int initTrajectory(EngineT *engine, ShotDataT *initialShotData);
void freeTrajectory(EngineT *engine);
int zeroAngle(EngineT *engine, ShotDataT *shotData, double distance, double *zeroAngle);
int trajectory(EngineT *engine, ShotDataT *shotData, double maxRange, double distStep,
               int extraData, double timeStep, TrajectoryTableT *resultTrajectory);
int integrate(EngineT *engine, double maxRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryTableT *trajectoryTable);

// helpers
double getCorrection(double distance, double offset);
double calculateEnergy(double bulletWeight, double velocity);
double calculateOGW(double bulletWeight, double velocity);

TrajectoryDataT createTrajectoryData(double time, V3dT rangeVector, V3dT velocityVector,
                                     double velocity, double mach, double spinDrift, double lookAngle,
                                     double densityFactor, double drag, double weight, int flag);

#endif // BC_H