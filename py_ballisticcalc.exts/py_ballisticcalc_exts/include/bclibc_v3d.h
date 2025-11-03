#ifndef BCLIBC_V3dT_H
#define BCLIBC_V3dT_H

#include <math.h> // For sqrt (for double precision)

// Structure definition and typedef for BCLIBC_V3dT
typedef struct
{
    double x;
    double y;
    double z;
} BCLIBC_V3dT;

#ifdef __cplusplus
extern "C"
{
#endif

    // Function Prototypes (Declarations) - UPDATED TO USE CONST POINTERS FOR INPUTS
    BCLIBC_V3dT BCLIBC_V3dT_new(double x, double y, double z);                 // Still takes values, creates new BCLIBC_V3dT
    BCLIBC_V3dT BCLIBC_V3dT_add(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2); // Takes const pointers
    BCLIBC_V3dT BCLIBC_V3dT_sub(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2); // Takes const pointers
    BCLIBC_V3dT BCLIBC_V3dT_mulS(const BCLIBC_V3dT *v, double scalar);         // Takes const pointer for BCLIBC_V3dT (changed from mul to mulS to match implementation)
    BCLIBC_V3dT BCLIBC_V3dT_neg(const BCLIBC_V3dT *v);                         // New negation function (takes const pointer)
    double BCLIBC_V3dT_dot(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2);      // Takes const pointers
    double BCLIBC_V3dT_mag(const BCLIBC_V3dT *v);                              // Takes const pointer
    void BCLIBC_V3dT_iNorm(BCLIBC_V3dT *v);                                    // Takes a non-const pointer, modifies in place
    BCLIBC_V3dT BCLIBC_V3dT_norm(const BCLIBC_V3dT *v);                        // Takes const pointer, returns a new BCLIBC_V3dT (changed from non-const pointer)
    void BCLIBC_V3dT_print(const char *name, const BCLIBC_V3dT *v);            // Takes const pointer for BCLIBC_V3dT

    //// --- New In-place Functions ---
    // void BCLIBC_V3dT_iadd(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2);
    // void BCLIBC_V3dT_isub(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2);
    // void BCLIBC_V3dT_imulS(BCLIBC_V3dT *v, double scalar);
    //
    //// --- New chainable In-place Functions ---
    // BCLIBC_V3dT* BCLIBC_V3dT_iaddc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2);
    // BCLIBC_V3dT* BCLIBC_V3dT_isubc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2);
    // BCLIBC_V3dT* BCLIBC_V3dT_imulSc(BCLIBC_V3dT *v, double scalar);
    // BCLIBC_V3dT* BCLIBC_V3dT_iNormc(BCLIBC_V3dT *v);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_V3dT_H
