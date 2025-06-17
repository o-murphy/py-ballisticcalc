#ifndef DRAG_H
#define DRAG_H

#include <stdlib.h>

typedef struct
{
    double CD;
    double Mach;
} DragTablePointT;

typedef struct
{
    DragTablePointT *table;
    size_t length;
} DragTableT;

typedef struct
{
    double a, b, c;
} CurvePointT;

typedef struct
{
    CurvePointT *points;
    size_t length;
} CurveT;

typedef struct
{
    double *values;
    size_t length;
} MachListT;

MachListT tableToMach(DragTableT *table);
CurveT calculateCurve(DragTableT *table);
double calculateByCurveAndMachList(MachListT *machList, CurveT *curve, double mach);
// Memory deallocation functions
void freeDragTable(DragTableT *table);
void freeCurve(CurveT *curve);
void freeMachList(MachListT *machList);

#endif // DRAG_H