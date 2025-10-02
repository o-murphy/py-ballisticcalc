# v3d.pxd

# Declare the C header file
cdef extern from "include/v3d.h" nogil:
    # Declare the V3dT structure
    ctypedef struct V3dT:
        double x
        double y
        double z

    # Declare the C function prototypes
    V3dT vec(double x, double y, double z) noexcept nogil
    V3dT add(const V3dT *v1, const V3dT *v2) noexcept nogil
    V3dT sub(const V3dT *v1, const V3dT *v2) noexcept nogil
    V3dT neg(const V3dT *v) noexcept nogil
    V3dT mulS(const V3dT *v, double scalar) noexcept nogil
    double dot(const V3dT *v1, const V3dT *v2) noexcept nogil
    double mag(const V3dT *v) noexcept nogil
    void iNorm(V3dT *v) noexcept nogil
    V3dT norm(const V3dT *v) noexcept nogil
    void print_vec(const char* name, const V3dT *v) noexcept nogil

    # # --- New In-place Functions ---
    # void iadd(V3dT *v1, const V3dT *v2)
    # void isub(V3dT *v1, const V3dT *v2)
    # void imulS(V3dT *v, double scalar)
    #
    # # --- New chainable In-place Functions ---
    # V3dT* iaddc(V3dT *v1, const V3dT *v2)
    # V3dT* isubc(V3dT *v1, const V3dT *v2)
    # V3dT* imulSc(V3dT *v, double scalar)
    # V3dT* iNormc(V3dT *v)
