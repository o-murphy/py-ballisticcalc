#ifndef TDATA_H
#define TDATA_H

#include "v3d.h"

typedef enum {
    NONE = 0,
    ZERO_UP = 1,
    ZERO_DOWN = 2,
    ZERO = ZERO_UP | ZERO_DOWN,
    MACH = 4,
    RANGE = 8,
    APEX = 16,
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX
} TrajFlagT;

typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajDataT;

#endif // TDATA_H
