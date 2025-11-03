#include "bclibc_v3d.h" // Include your own header file
#include <math.h>       // Required for fabs and sqrt
#include <stdio.h>      // Required for printf (if print_vec is kept)

// Function Implementations

// Creates a new BCLIBC_V3dT from given components
BCLIBC_V3dT BCLIBC_V3dT_new(double x, double y, double z)
{
    return (BCLIBC_V3dT){.x = x, .y = y, .z = z};
}

// Adds two BCLIBC_V3dT vectors (takes const pointers for efficiency)
BCLIBC_V3dT BCLIBC_V3dT_add(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
{
    return (BCLIBC_V3dT){
        .x = v1->x + v2->x,
        .y = v1->y + v2->y,
        .z = v1->z + v2->z};
}

// Subtracts two BCLIBC_V3dT vectors (takes const pointers for efficiency)
BCLIBC_V3dT BCLIBC_V3dT_sub(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
{
    return (BCLIBC_V3dT){
        .x = v1->x - v2->x,
        .y = v1->y - v2->y,
        .z = v1->z - v2->z};
}

// Negates a BCLIBC_V3dT vector (multiplies by -1)
BCLIBC_V3dT BCLIBC_V3dT_neg(const BCLIBC_V3dT *v)
{
    return (BCLIBC_V3dT){
        .x = -v->x,
        .y = -v->y,
        .z = -v->z};
}

// Multiplies a BCLIBC_V3dT vector by a scalar (takes const pointer for efficiency)
BCLIBC_V3dT BCLIBC_V3dT_mulS(const BCLIBC_V3dT *v, double scalar)
{
    return (BCLIBC_V3dT){
        .x = v->x * scalar,
        .y = v->y * scalar,
        .z = v->z * scalar};
}

// Computes the dot product of two BCLIBC_V3dT vectors (takes const pointers for efficiency)
double BCLIBC_V3dT_dot(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
{
    return (v1->x * v2->x) + (v1->y * v2->y) + (v1->z * v2->z);
}

// Computes the magnitude (length) of a BCLIBC_V3dT vector (takes const pointer for efficiency)
double BCLIBC_V3dT_mag(const BCLIBC_V3dT *v)
{
    return sqrt((v->x * v->x) + (v->y * v->y) + (v->z * v->z));
}

// Normalizes a BCLIBC_V3dT vector in place (modifies the original vector)
void BCLIBC_V3dT_iNorm(BCLIBC_V3dT *v)
{
    double m = BCLIBC_V3dT_mag(v);

    if (fabs(m) < 1e-10)
    {
        return; // Do nothing if magnitude is near zero (matching Cython behavior)
    }
    else
    {
        *v = BCLIBC_V3dT_mulS(v, 1.0 / m); // Reuse mulS for in-place normalization
    }
}

// Returns a new normalized BCLIBC_V3dT vector (does not modify the original)
BCLIBC_V3dT BCLIBC_V3dT_norm(const BCLIBC_V3dT *v)
{
    double m = BCLIBC_V3dT_mag(v);

    if (fabs(m) < 1e-10)
    {
        // Return the original vector unchanged if magnitude is near zero (matching Cython behavior)
        return (BCLIBC_V3dT){.x = v->x, .y = v->y, .z = v->z};
    }
    else
    {
        return BCLIBC_V3dT_mulS(v, 1.0 / m); // Reuse mulS for normalization
    }
}

// Prints a BCLIBC_V3dT vector to the console
void BCLIBC_V3dT_print(const char *name, const BCLIBC_V3dT *v)
{
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v->x, v->y, v->z);
}

//// --- New In-place Functions ---
//
//// Adds v2 to v1 in-place (modifies v1)
// void BCLIBC_V3dT_iadd(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) {
//     v1->x += v2->x;
//     v1->y += v2->y;
//     v1->z += v2->z;
// }
//
//// Subtracts v2 from v1 in-place (modifies v1)
// void isub(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) {
//     v1->x -= v2->x;
//     v1->y -= v2->y;
//     v1->z -= v2->z;
// }
//
//// Multiplies v by scalar in-place (modifies v)
// void BCLIBC_V3dT_imulS(BCLIBC_V3dT *v, double scalar) {
//     v->x *= scalar;
//     v->y *= scalar;
//     v->z *= scalar;
// }
//
//// --- New chainable In-place Functions ---
//
//// Adds v2 to v1 in-place (modifies v1)
// BCLIBC_V3dT* BCLIBC_V3dT_iaddc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) {
//     v1->x += v2->x;
//     v1->y += v2->y;
//     v1->z += v2->z;
//     return v1;
// }
//
//// Subtracts v2 from v1 in-place (modifies v1)
// BCLIBC_V3dT* BCLIBC_V3dT_isubc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) {
//     v1->x -= v2->x;
//     v1->y -= v2->y;
//     v1->z -= v2->z;
//     return v1;
// }
//
//// Multiplies v by scalar in-place (modifies v)
// BCLIBC_V3dT* BCLIBC_V3dT_imulSc(BCLIBC_V3dT *v, double scalar) {
//     v->x *= scalar;
//     v->y *= scalar;
//     v->z *= scalar;
//     return v;
// }
//
//// Normalizes a BCLIBC_V3dT vector in place (modifies the original vector)
// BCLIBC_V3dT* BCLIBC_V3dT_iNormc(BCLIBC_V3dT *v) {
//     double m = BCLIBC_V3dT_mag(v);
//
//     if (fabs(m) < 1e-10) {
//         return v; // Do nothing if magnitude is near zero (matching Cython behavior)
//     } else {
//         *v = BCLIBC_V3dT_mulS(v, 1.0 / m); // Reuse mulS for in-place normalization
//         return v;
//     }
// }
