#ifndef WIND_H
#define WIND_H

#include "v3d.h"


typedef struct
{
    double velocity;
    double directionFrom;
    double untilDistance;
    double MAX_DISTANCE_FEET;
} WindT;

V3dT windToVector(const WindT *w);

typedef struct
{
    WindT *winds;
    size_t length;
} WindsT;

typedef struct
{
    WindsT *winds;
    int current;
    double nextRange;
    V3dT lastVectorCache;
} WindSockT;

int initWindSock(WindSockT *ws, WindsT *winds);
V3dT currentWindVector(WindSockT *ws);
void updateWindCache(WindSockT *ws);
V3dT windVectorForRange(WindSockT *ws, double nextRange);

#endif // WIND_H