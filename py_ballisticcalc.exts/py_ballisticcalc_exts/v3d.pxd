# Declare the C header file
cdef extern from "include/bclibc/v3d.hpp" namespace "bclibc" nogil:
    # Declare the BCLIBC_V3dT structure
    cdef cppclass BCLIBC_V3dT:
        double x
        double y
        double z

        BCLIBC_V3dT() except +
        BCLIBC_V3dT(double x, double y, double z) except +

        # Arithmetic operators (create new vectors)
        BCLIBC_V3dT operator+(const BCLIBC_V3dT &other) const
        BCLIBC_V3dT operator-() const
        BCLIBC_V3dT operator-(const BCLIBC_V3dT &other) const
        BCLIBC_V3dT operator*(double scalar) const
        BCLIBC_V3dT operator/(double scalar) const

        # Dot product
        double operator*(const BCLIBC_V3dT &other) const

        # Compound assignment operators
        BCLIBC_V3dT &add_eq "operator+=" (const BCLIBC_V3dT &other)
        BCLIBC_V3dT &sub_eq "operator-=" (const BCLIBC_V3dT &other)
        BCLIBC_V3dT &mul_eq "operator*=" (double scalar)
        BCLIBC_V3dT &div_eq "operator/=" (double scalar)

        # Optimized fused operations
        BCLIBC_V3dT &fused_multiply_add(const BCLIBC_V3dT &other, double scalar)
        BCLIBC_V3dT &fused_multiply_subtract(const BCLIBC_V3dT &other, double scalar)
        BCLIBC_V3dT &linear_combination(
            const BCLIBC_V3dT &vec_a, double scalar_a,
            const BCLIBC_V3dT &vec_b, double scalar_b)
        BCLIBC_V3dT &linear_combination_4(
            const BCLIBC_V3dT &v_a, double s_a,
            const BCLIBC_V3dT &v_b, double s_b,
            const BCLIBC_V3dT &v_c, double s_c,
            const BCLIBC_V3dT &v_d, double s_d)

        # Vector properties
        double mag() const
        double mag_squared() const
        BCLIBC_V3dT norm() const
        BCLIBC_V3dT &normalize()

    # Non-member function for scalar * vector
    BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT& vec)
