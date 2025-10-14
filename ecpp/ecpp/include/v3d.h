#ifndef V3DC_H
#define V3DC_H

#include <stdio.h>

// 24 bytes (3 x double)
typedef struct V3dT {
    double x;
    double y;
    double z;
} V3dT;

// --- Non-in-place operations (Pass-by-Value) ---

// Creates a new V3dT from given components
V3dT vec(double x, double y, double z);

// Vector Addition: v1 + v2
V3dT add(V3dT v1, V3dT v2);

// Vector Subtraction: v1 - v2
V3dT sub(V3dT v1, V3dT v2);

// Vector Negation: -v
V3dT neg(V3dT v);

// Scalar Multiplication: v * scalar
V3dT mulS(V3dT v, double scalar);

// Dot Product: v1 . v2
double dot(V3dT v1, V3dT v2);

// Magnitude (Length)
double mag(V3dT v);

// Returns a new normalized V3dT vector
V3dT norm(V3dT v);


// --- In-place operations (Pass-by-Pointer) ---
// Note: In-place functions MUST use pointers to modify the original variable.

// Normalizes a V3dT vector in place (modifies the original vector)
void iNorm(V3dT *v);


// --- Utility ---
void print_vec(const char *name, V3dT v);

#endif // V3DC_H
