#ifndef EULER_H
#define EULER_H

#include "v3d.h"

typedef struct  {
    double time;
    V3dT wind_vector;
    V3dT range_vector;
    V3dT velocity_vector;
    double velocity;
    double mach;
    double density_factor;
    double drag;
} BaseIntegrationStateT;

#endif // EULER_H