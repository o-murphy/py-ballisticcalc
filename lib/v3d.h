#ifndef V3D_H
#define V3D_H

#include <math.h> // For sqrt (for double precision)
#include <stdio.h> // For print_vec

// Structure definition and typedef for V3d
typedef struct {
    double x;
    double y;
    double z;
} V3d;

// Function Prototypes (Declarations) - UPDATED TO USE CONST POINTERS FOR INPUTS
V3d set(double x, double y, double z); // Still takes values, creates new V3d
V3d add(const V3d *v1, const V3d *v2); // Takes const pointers
V3d sub(const V3d *v1, const V3d *v2); // Takes const pointers
V3d mulS(const V3d *v, double scalar); // Takes const pointer for V3d
double dot(const V3d *v1, const V3d *v2); // Takes const pointers
double mag(const V3d *v); // Takes const pointer
void norm(V3d *v); // Takes a non-const pointer, modifies in place
void print_vec(const char* name, const V3d *v); // Takes const pointer for V3d

#endif // V3D_H