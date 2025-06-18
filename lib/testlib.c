#include "testlib.h"
#include <stdlib.h>
#include <stdio.h>

int f1(TrajectoryTable *t) {
    printf("f1: t = %p\n", (void*)t);
    if (!t) return -1;
    t->length = 3;
    t->data = (double *)malloc(t->length * sizeof(double));
    if (!t->data) return -2;
    for (size_t i = 0; i < t->length; ++i) {
        t->data[i] = i * 1.1;
    }
    return 0;
}

int f2(TrajectoryTable *t) {
    printf("f2: t = %p\n", (void*)t);
    return f1(t);
}

void free_table(TrajectoryTable *t) {
    if (t && t->data) {
        printf("free_table: freeing data at %p\n", (void*)t->data);
        free(t->data);
        t->data = NULL;
        t->length = 0;
    }
}
