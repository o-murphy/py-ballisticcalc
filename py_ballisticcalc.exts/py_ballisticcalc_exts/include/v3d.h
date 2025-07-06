#ifndef V3dT_H
#define V3dT_H

#include <math.h> // For sqrt (for double precision)
#include <stdio.h> // For print_vec

// Structure definition and typedef for V3dT
typedef struct {
    double x;
    double y;
    double z;
} V3dT;

// Function Prototypes (Declarations) - UPDATED TO USE CONST POINTERS FOR INPUTS
V3dT set(double x, double y, double z);                  // Still takes values, creates new V3dT
V3dT add(const V3dT *v1, const V3dT *v2);                // Takes const pointers
V3dT sub(const V3dT *v1, const V3dT *v2);                // Takes const pointers
V3dT mulS(const V3dT *v, double scalar);                 // Takes const pointer for V3dT (changed from mul to mulS to match implementation)
V3dT neg(const V3dT *v);                                 // New negation function (takes const pointer)
double dot(const V3dT *v1, const V3dT *v2);              // Takes const pointers
double mag(const V3dT *v);                               // Takes const pointer
void iNorm(V3dT *v);                                     // Takes a non-const pointer, modifies in place
V3dT norm(const V3dT *v);                                // Takes const pointer, returns a new V3dT (changed from non-const pointer)
void print_vec(const char* name, const V3dT *v);         // Takes const pointer for V3dT

//// --- New In-place Functions ---
//void iadd(V3dT *v1, const V3dT *v2);
//void isub(V3dT *v1, const V3dT *v2);
//void imulS(V3dT *v, double scalar);
//
//// --- New chainable In-place Functions ---
//V3dT* iaddc(V3dT *v1, const V3dT *v2);
//V3dT* isubc(V3dT *v1, const V3dT *v2);
//V3dT* imulSc(V3dT *v, double scalar);
//V3dT* iNormc(V3dT *v);

#endif // V3dT_H