# Declare the C header file
cdef extern from "include/bclibc/v3d.hpp" namespace "bclibc" nogil:
    # Declare the BCLIBC_V3dT structure
    cdef cppclass BCLIBC_V3dT:
        double x
        double y
        double z

        BCLIBC_V3dT() except+
        BCLIBC_V3dT(double x, double y, double z) except+

        BCLIBC_V3dT operator+(const BCLIBC_V3dT &other) const
        BCLIBC_V3dT operator-() const
        BCLIBC_V3dT operator-(const BCLIBC_V3dT &other) const
        BCLIBC_V3dT operator*(double scalar) const
        BCLIBC_V3dT operator/(double scalar) const

        double operator*(const BCLIBC_V3dT &other) const

        BCLIBC_V3dT &add_eq "operator+=" (const BCLIBC_V3dT &other)
        BCLIBC_V3dT &sub_eq "operator-=" (const BCLIBC_V3dT &other)
        BCLIBC_V3dT &mul_eq "operator*=" (double scalar)
        BCLIBC_V3dT &div_eq "operator/=" (double scalar)

        double mag() const
        BCLIBC_V3dT norm() const

    BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT& vec)
