#ifndef TFILTER_H
#define TFILTER_H

#include "v3d.h"
#include "tflag.h"
#include <stdbool.h>



typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTData;

typedef struct {
    enum TFlag filter;
    enum TFlag currentFlag;
    enum TFlag seenZero;
    double timeStep;
    double rangeStep;
    double timeOfLastRecord;
    double nextRecordDistance;
    double previousMach;
    double previousTime;
    V3dT previousPosition;
    V3dT previousVelocity;
    double previousVMach;
    double lookAngle;

    BaseTData *data;  // NULL by default
} TDataFilter;

// Публічні функції
bool TDataFilter_init(
    TDataFilter *tdf,
    enum TFlag filterFlags,
    double rangeStep,
    const V3dT *initialPosition,
    const V3dT *initialVelocity,
    double timeStep
);

bool TDataFilter_initWithDefaultTimeStep( // Змінено на int
    TDataFilter *tdf,
    enum TFlag filterFlags,
    double rangeStep,
    const V3dT *initialPosition,
    const V3dT *initialVelocity
);

void TDataFilter_free(
    TDataFilter *tdf
);

void TDataFilter_setupSeenZero(
    TDataFilter *tdf,
    double height,
    double barrelElevation,
    double lookAngle
);

bool TDataFilter_shouldRecord(
    TDataFilter *tdf,
    const V3dT *position,
    const V3dT *velocity,
    double mach,
    double time
);

// Приватні (static) функції не оголошуються в .h файлі.

#endif // TFILTER_H