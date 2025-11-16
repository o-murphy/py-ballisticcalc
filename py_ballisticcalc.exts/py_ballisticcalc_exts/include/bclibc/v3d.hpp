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
    };

    BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT &vec);
};

#endif // BCLIBC_V3dT_HPP