#ifndef TDATAFILTER_H
#define TDATAFILTER_H

#include "v3d.h"


// Corrected BaseTrajData struct (already good, just adding for completeness)
typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajDataT;

typedef struct {
    int filter, currentFlag, seenZero;
    double timeStep, rangeStep;
    double timeOfLastRecord, nextRecordDistance;
    double previousMach, previousTime;
    V3dT previousPosition, previousVelocity;
    double previousVMach;
    double lookAngle;
} TrajectoryDataFilterT;

int initDataFilter(TrajectoryDataFilterT *tdf, int filterFlags, double rangeStep,
                   V3dT initialPosition, V3dT initialVelocity, double timeStep);
void setupSeenZero(TrajectoryDataFilterT * tdf, double height, double barrelElevation, double lookAngle);
void checkNextTime(TrajectoryDataFilterT *tdf, double time);
void checkMachCrossing(TrajectoryDataFilterT *tdf, double velocity, double mach);
void checkZeroCrossing(TrajectoryDataFilterT *tdf, V3dT rangeVector);
BaseTrajDataT* shouldRecord(TrajectoryDataFilterT *tdf, V3dT position, V3dT velocity, double mach, double time);

#endif // TDATAFILTER_H
