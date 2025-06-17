// vec3.h
#ifndef VEC3_H
#define VEC3_H

#include <math.h> // For sqrtf (used by mag and norm)

// Structure definition and typedef for Vec3
typedef struct {
    float x;
    float y;
    float z;
} Vec3;

// Function Prototypes (Declarations)
Vec3 set(float x, float y, float z);
Vec3 add(Vec3 v1, Vec3 v2);
Vec3 sub(Vec3 v1, Vec3 v2);
Vec3 mulS(Vec3 v, float scalar);
float dot(Vec3 v1, Vec3 v2);
float mag(Vec3 v);
void norm(Vec3 *v);
void print_vec(const char* name, Vec3 v);

#endif // VEC3_H

