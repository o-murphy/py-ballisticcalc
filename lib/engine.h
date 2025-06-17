#ifndef ENGINE_H
#define ENGINE_H

#include <math.h>
#include "v3d.h"
#include "bindings.h"
#include "trajectoryData.h"

typedef struct {
    int filter, currentFlag, seenZero;
    double timeStep, rangeStep;
    double timeOfLastRecord, nextRecordDistance;
    double previousMach, previousTime;
    V3d previousPosition, previousVelocity;
    double previousVMach;
    double lookAngle;
} TrajectoryDataFilterT;

TrajectoryDataFilterT createTrajectoryDataFilterT(
    int filterFlags, double rangeStep,
    V3d initialPosition, V3d initialVelocity,
    double timeStep
);
void setupSeenZero(TrajectoryDataFilterT * tdf, double height, double barrelElevation, double lookAngle);
static void checkNextTime(TrajectoryDataFilterT *tdf, double time);
static void checkMachCrossing(TrajectoryDataFilterT *tdf, double velocity, double mach);
static void checkZeroCrossing(TrajectoryDataFilterT *tdf, V3d rangeVector);
BaseTrajDataT* shouldRecord(TrajectoryDataFilterT *tdf, V3d position, V3d velocity, double mach, double time);

typedef struct {
    WindT * winds;
    int length;
    int current;
    V3d lastVectorCache;
} WindSockT;

V3d currentVector(WindSockT * ws);
void updateCache(WindSockT * ws);
V3d vectorForRange(WindSockT * ws, double nextRange);

// // --- EngineT Definition ---
// typedef struct {
//     ConfigT config;
//     V3d gravityVector;
//     DragTableT tableData;
//     WindSockT ws;
//     ShotDataT sd;
// } EngineT;

// EngineT createEngine(ConfigT * config);

// --- EngineT Function Prototypes ---
// void initTrajectory(EngineT *engine);
// void freeTrajectory(EngineT *engine);
// // Corrected: 'double distance'
// int zeroAngle(EngineT *engine, ShotDataT *shotData, double distance, double * zeroAngle);
// // Corrected: Uses TrajectoryData (assuming TrajectoryData is the typedef name for the struct)
// int integrate(EngineT *engine, double maximumRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryData * ranges);


#endif // ENGINE_H