#ifndef TESTLIB_H
#define TESTLIB_H

#include <stddef.h>  // for size_t

typedef struct {
    double *data;
    size_t length;
} TrajectoryTable;

int f1(TrajectoryTable *t);
int f2(TrajectoryTable *t);
void free_table(TrajectoryTable *t);

#endif // TESTLIB_H