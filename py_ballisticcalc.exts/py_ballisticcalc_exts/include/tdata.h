#ifndef TDATA_H
#define TDATA_H

#include "v3d.h"

typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajData;

#endif // TDATA_H