// V3d.h
#ifndef V3D_H
#define V3D_H

#include <math.h> // For sqrtf (used by mag and norm)

// Structure definition and typedef for V3d
typedef struct {
    float x;
    float y;
    float z;
} V3d;

// Function Prototypes (Declarations)
V3d set(float x, float y, float z);
V3d add(V3d v1, V3d v2);
V3d sub(V3d v1, V3d v2);
V3d mulS(V3d v, float scalar);
float dot(V3d v1, V3d v2);
float mag(V3d v);
void norm(V3d *v);
void print_vec(const char* name, V3d v);

#endif // V3D_H

