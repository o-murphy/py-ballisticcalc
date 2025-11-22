#ifndef BCLIBC_V3dT_HPP
#define BCLIBC_V3dT_HPP

namespace bclibc
{

    // Structure definition and typedef for BCLIBC_V3dT
    struct BCLIBC_V3dT
    {
    public:
        double x;
        double y;
        double z;

        BCLIBC_V3dT() = default;
        BCLIBC_V3dT(double x, double y, double z);

        BCLIBC_V3dT operator+(const BCLIBC_V3dT &other) const;
        BCLIBC_V3dT operator-() const;
        BCLIBC_V3dT operator-(const BCLIBC_V3dT &other) const;
        BCLIBC_V3dT operator*(double scalar) const;
        BCLIBC_V3dT operator/(double scalar) const;

        double operator*(const BCLIBC_V3dT &other) const;

        BCLIBC_V3dT &operator+=(const BCLIBC_V3dT &other);
        BCLIBC_V3dT &operator-=(const BCLIBC_V3dT &other);
        BCLIBC_V3dT &operator*=(double scalar);
        BCLIBC_V3dT &operator/=(double scalar);

        double mag() const;
        BCLIBC_V3dT norm() const;

        BCLIBC_V3dT &fused_multiply_add(const BCLIBC_V3dT &other, double scalar);
        BCLIBC_V3dT &fused_multiply_subtract(const BCLIBC_V3dT &other, double scalar);

        BCLIBC_V3dT &linear_combination(
            const BCLIBC_V3dT &vec_a, double scalar_a,
            const BCLIBC_V3dT &vec_b, double scalar_b);
        BCLIBC_V3dT &linear_combination_4(
            const BCLIBC_V3dT &v_a, double s_a,
            const BCLIBC_V3dT &v_b, double s_b,
            const BCLIBC_V3dT &v_c, double s_c,
            const BCLIBC_V3dT &v_d, double s_d);

        double mag_squared() const;
        BCLIBC_V3dT &normalize();
    };

    BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT &vec);
};

#endif // BCLIBC_V3dT_HPP