#include "v3d.h" // Include your own header file

// Function Implementations

// Creates a new V3d from given components
V3d set(double x, double y, double z) {
    V3d v = {x, y, z};
    return v;
}

// Adds two V3d vectors (takes const pointers for efficiency)
V3d add(const V3d *v1, const V3d *v2) {
    V3d result;
    result.x = v1->x + v2->x; // Use -> for pointer access
    result.y = v1->y + v2->y;
    result.z = v1->z + v2->z;
    return result;
}

// Subtracts two V3d vectors (takes const pointers for efficiency)
V3d sub(const V3d *v1, const V3d *v2) {
    V3d result;
    result.x = v1->x - v2->x; // Use -> for pointer access
    result.y = v1->y - v2->y;
    result.z = v1->z - v2->z;
    return result;
}

// Multiplies a V3d vector by a scalar (takes const pointer for efficiency)
V3d mulS(const V3d *v, double scalar) {
    V3d result;
    result.x = v->x * scalar; // Use -> for pointer access
    result.y = v->y * scalar;
    result.z = v->z * scalar;
    return result;
}

// Computes the dot product of two V3d vectors (takes const pointers for efficiency)
double dot(const V3d *v1, const V3d *v2) {
    return (v1->x * v2->x) + (v1->y * v2->y) + (v1->z * v2->z); // Use -> for pointer access
}

// Computes the magnitude (length) of a V3d vector (takes const pointer for efficiency)
double mag(const V3d *v) {
    // Use sqrt for double precision, as V3d components are double
    return sqrt((v->x * v->x) + (v->y * v->y) + (v->z * v->z)); // Use -> for pointer access
}

// Normalizes a V3d vector in place (modifies the original vector)
void norm(V3d *v) {
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

// Prints a V3d vector to the console
void print_vec(const char* name, const V3d *v) {
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v->x, v->y, v->z); // Use -> for pointer access
}