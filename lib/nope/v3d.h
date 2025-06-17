// v3d.h (Header file, remains separate)
#ifndef V3D_H
#define V3D_H

#include <math.h> // For sqrt (for double precision, not sqrtf)
#include <stdio.h> // For print_vec

// Structure definition and typedef for V3d
typedef struct {
    double x;
    double y;
    double z;
} V3d;

// Function Prototypes (Declarations)
V3d set(double x, double y, double z);
V3d add(V3d v1, V3d v2);
V3d sub(V3d v1, V3d v2);
V3d mulS(V3d v, double scalar);
double dot(V3d v1, V3d v2);
double mag(V3d v);
void norm(V3d *v);
void print_vec(const char* name, V3d v); // Added to your header

#endif // V3D_H