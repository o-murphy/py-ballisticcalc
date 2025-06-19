#include "v3d.h" // Include your own header file

// Function Implementations

// Creates a new V3dT from given components
V3dT set(double x, double y, double z) {
    V3dT v = {x, y, z};
    return v;
}

// Adds two V3dT vectors (takes const pointers for efficiency)
V3dT add(const V3dT *v1, const V3dT *v2) {
    V3dT result;
    result.x = v1->x + v2->x; // Use -> for pointer access
    result.y = v1->y + v2->y;
    result.z = v1->z + v2->z;
    return result;
}

// Subtracts two V3dT vectors (takes const pointers for efficiency)
V3dT sub(const V3dT *v1, const V3dT *v2) {
    V3dT result;
    result.x = v1->x - v2->x; // Use -> for pointer access
    result.y = v1->y - v2->y;
    result.z = v1->z - v2->z;
    return result;
}

// Negates a V3dT vector (multiplies by -1)
V3dT neg(const V3dT *v) {
    V3dT result;
    result.x = -v->x;
    result.y = -v->y;
    result.z = -v->z;
    return result;
}

// Multiplies a V3dT vector by a scalar (takes const pointer for efficiency)
V3dT mulS(const V3dT *v, double scalar) {
    V3dT result;
    result.x = v->x * scalar; // Use -> for pointer access
    result.y = v->y * scalar;
    result.z = v->z * scalar;
    return result;
}

// Computes the dot product of two V3dT vectors (takes const pointers for efficiency)
double dot(const V3dT *v1, const V3dT *v2) {
    return (v1->x * v2->x) + (v1->y * v2->y) + (v1->z * v2->z); // Use -> for pointer access
}

// Computes the magnitude (length) of a V3dT vector (takes const pointer for efficiency)
double mag(const V3dT *v) {
    // Use sqrt for double precision, as V3dT components are double
    return sqrt((v->x * v->x) + (v->y * v->y) + (v->z * v->z)); // Use -> for pointer access
}

// Normalizes a V3dT vector in place (modifies the original vector)
void iNorm(V3dT *v) {
    double m = mag(v); // Pass pointer to mag function
    if (m == 0.0) { // Use 0.0 for double comparisons
        printf("Warning: Cannot normalize a zero vector.\n");
        v->x = 0.0;
        v->y = 0.0;
        v->z = 0.0;
    } else {
        v->x /= m;
        v->y /= m;
        v->z /= m;
    }
}

// Returns a new normalized V3dT vector (does not modify the original)
V3dT norm(const V3dT *v) { // Parameter updated to const V3dT *v
    double m = mag(v);
    V3dT nv; // Declare the new vector

    if (m == 0.0) {
        printf("Warning: Cannot normalize a zero vector. Returning zero vector.\n");
        nv = (V3dT){.x = 0.0, .y = 0.0, .z = 0.0}; // Corrected: assign to nv, add semicolon
    } else {
        nv = (V3dT){.x = v->x / m, .y = v->y / m, .z = v->z / m}; // Corrected: assign to nv, add semicolon
    }
    return nv; // Return the new vector
}

// Prints a V3dT vector to the console
void print_vec(const char* name, const V3dT *v) {
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v->x, v->y, v->z); // Use -> for pointer access
}
