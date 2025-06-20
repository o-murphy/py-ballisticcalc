#include "v3d.h" // Include your own header file
#include <math.h> // Required for fabs and sqrt
#include <stdio.h> // Required for printf (if print_vec is kept)

// Function Implementations

// Creates a new V3dT from given components
V3dT set(double x, double y, double z) {
    return (V3dT){.x = x, .y = y, .z = z};
}

// Adds two V3dT vectors (takes const pointers for efficiency)
V3dT add(const V3dT *v1, const V3dT *v2) {
    return (V3dT){
        .x = v1->x + v2->x,
        .y = v1->y + v2->y,
        .z = v1->z + v2->z
    };
}

// Subtracts two V3dT vectors (takes const pointers for efficiency)
V3dT sub(const V3dT *v1, const V3dT *v2) {
    return (V3dT){
        .x = v1->x - v2->x,
        .y = v1->y - v2->y,
        .z = v1->z - v2->z
    };
}

// Negates a V3dT vector (multiplies by -1)
V3dT neg(const V3dT *v) {
    return (V3dT){
        .x = -v->x,
        .y = -v->y,
        .z = -v->z
    };
}

// Multiplies a V3dT vector by a scalar (takes const pointer for efficiency)
V3dT mulS(const V3dT *v, double scalar) {
    return (V3dT){
        .x = v->x * scalar,
        .y = v->y * scalar,
        .z = v->z * scalar
    };
}

// Computes the dot product of two V3dT vectors (takes const pointers for efficiency)
double dot(const V3dT *v1, const V3dT *v2) {
    return (v1->x * v2->x) + (v1->y * v2->y) + (v1->z * v2->z);
}

// Computes the magnitude (length) of a V3dT vector (takes const pointer for efficiency)
double mag(const V3dT *v) {
    return sqrt((v->x * v->x) + (v->y * v->y) + (v->z * v->z));
}

// Normalizes a V3dT vector in place (modifies the original vector)
void iNorm(V3dT *v) {
    double m = mag(v);

    if (fabs(m) < 1e-10) {
        return; // Do nothing if magnitude is near zero (matching Cython behavior)
    } else {
        *v = mulS(v, 1.0 / m); // Reuse mulS for in-place normalization
    }
}

// Returns a new normalized V3dT vector (does not modify the original)
V3dT norm(const V3dT *v) {
    double m = mag(v);

    if (fabs(m) < 1e-10) {
        // Return the original vector unchanged if magnitude is near zero (matching Cython behavior)
        return (V3dT){.x = v->x, .y = v->y, .z = v->z};
    } else {
        return mulS(v, 1.0 / m); // Reuse mulS for normalization
    }
}

// Prints a V3dT vector to the console
void print_vec(const char* name, const V3dT *v) {
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v->x, v->y, v->z);
}