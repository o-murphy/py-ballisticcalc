# Declare the C header file
cdef extern from "include/bclibc_v3d.h" nogil:
    # Declare the BCLIBC_V3dT structure
    ctypedef struct BCLIBC_V3dT:
        double x
        double y
        double z

    # Declare the C function prototypes
    BCLIBC_V3dT BCLIBC_V3dT_new(double x, double y, double z) noexcept nogil
    BCLIBC_V3dT BCLIBC_V3dT_add(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) noexcept nogil
    BCLIBC_V3dT BCLIBC_V3dT_sub(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) noexcept nogil
    BCLIBC_V3dT BCLIBC_V3dT_neg(const BCLIBC_V3dT *v) noexcept nogil
    BCLIBC_V3dT BCLIBC_V3dT_mulS(const BCLIBC_V3dT *v, double scalar) noexcept nogil
    double BCLIBC_V3dT_dot(const BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2) noexcept nogil
    double BCLIBC_V3dT_mag(const BCLIBC_V3dT *v) noexcept nogil
    # void BCLIBC_V3dT_iNorm(BCLIBC_V3dT *v) noexcept nogil
    BCLIBC_V3dT BCLIBC_V3dT_norm(const BCLIBC_V3dT *v) noexcept nogil
    void BCLIBC_V3dT_print(const char* name, const BCLIBC_V3dT *v) noexcept nogil

    # # --- New In-place Functions ---
    # void BCLIBC_V3dT_iadd(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
    # void BCLIBC_V3dT_isub(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
    # void BCLIBC_V3dT_imulS(BCLIBC_V3dT *v, double scalar)
    #
    # # --- New chainable In-place Functions ---
    # BCLIBC_V3dT* iaddc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
    # BCLIBC_V3dT* isubc(BCLIBC_V3dT *v1, const BCLIBC_V3dT *v2)
    # BCLIBC_V3dT* imulSc(BCLIBC_V3dT *v, double scalar)
    # BCLIBC_V3dT* iNormc(BCLIBC_V3dT *v)
