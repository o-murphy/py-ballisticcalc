#include "v3d.h"
#include <math.h>  // Required for fabs and sqrt
#include <stdio.h> // Required for printf

// Function Implementations (Pass-by-Value)

// Creates a new V3dT from given components
V3dT vec(double x, double y, double z)
{
    return (V3dT){.x = x, .y = y, .z = z};
}

// Adds two V3dT vectors
V3dT add(V3dT v1, V3dT v2)
{
    return (V3dT){
        .x = v1.x + v2.x,
        .y = v1.y + v2.y,
        .z = v1.z + v2.z};
}

// Subtracts two V3dT vectors
V3dT sub(V3dT v1, V3dT v2)
{
    return (V3dT){
        .x = v1.x - v2.x,
        .y = v1.y - v2.y,
        .z = v1.z - v2.z};
}

// Negates a V3dT vector
V3dT neg(V3dT v)
{
    return (V3dT){
        .x = -v.x,
        .y = -v.y,
        .z = -v.z};
}

// Multiplies a V3dT vector by a scalar
V3dT mulS(V3dT v, double scalar)
{
    return (V3dT){
        .x = v.x * scalar,
        .y = v.y * scalar,
        .z = v.z * scalar};
}

// Computes the dot product of two V3dT vectors
double dot(V3dT v1, V3dT v2)
{
    return (v1.x * v2.x) + (v1.y * v2.y) + (v1.z * v2.z);
}

// Computes the magnitude (length) of a V3dT vector
double mag(V3dT v)
{
    return sqrt((v.x * v.x) + (v.y * v.y) + (v.z * v.z));
}

// Normalizes a V3dT vector in place (uses pointer)
void iNorm(V3dT *v)
{
    double m = mag(*v); // Pass structure by value to mag

    if (fabs(m) < 1e-10)
    {
        return;
    }
    else
    {
        // Use non-in-place mulS and assign result back to *v
        *v = mulS(*v, 1.0 / m);
    }
}

// Returns a new normalized V3dT vector
V3dT norm(V3dT v)
{
    double m = mag(v);

    if (fabs(m) < 1e-10)
    {
        return v;
    }
    else
    {
        return mulS(v, 1.0 / m);
    }
}

// Prints a V3dT vector to the console
void print_vec(const char *name, V3dT v)
{
    printf("%s = (%.2f, %.2f, %.2f)\n", name, v.x, v.y, v.z);
}
