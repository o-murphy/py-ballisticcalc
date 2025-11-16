#include <cmath>          // Required for fabs and sqrt
#include "bclibc/v3d.hpp" // Include your own header file

namespace bclibc
{

    // Function Implementations

    BCLIBC_V3dT::BCLIBC_V3dT(double x, double y, double z)
        : x(x), y(y), z(z) {};

    BCLIBC_V3dT BCLIBC_V3dT::operator+(const BCLIBC_V3dT &other) const
    {
        return BCLIBC_V3dT(x + other.x, y + other.y, z + other.z);
    }

    BCLIBC_V3dT BCLIBC_V3dT::operator-() const
    {
        return BCLIBC_V3dT(-x, -y, -z);
    }

    BCLIBC_V3dT BCLIBC_V3dT::operator-(const BCLIBC_V3dT &other) const
    {
        return BCLIBC_V3dT(x - other.x, y - other.y, z - other.z);
    }

    BCLIBC_V3dT BCLIBC_V3dT::operator*(double scalar) const
    {
        return BCLIBC_V3dT(x * scalar, y * scalar, z * scalar);
    }

    BCLIBC_V3dT BCLIBC_V3dT::operator/(double scalar) const
    {
        if (std::fabs(scalar) < 1e-10)
        {
            return *this;
        }
        return (*this) * (1.0 / scalar);
    }

    double BCLIBC_V3dT::operator*(const BCLIBC_V3dT &other) const
    {
        return (x * other.x) + (y * other.y) + (z * other.z);
    }

    BCLIBC_V3dT &BCLIBC_V3dT::operator+=(const BCLIBC_V3dT &other)
    {
        x += other.x;
        y += other.y;
        z += other.z;
        return *this;
    }

    BCLIBC_V3dT &BCLIBC_V3dT::operator-=(const BCLIBC_V3dT &other)
    {
        x -= other.x;
        y -= other.y;
        z -= other.z;
        return *this;
    }

    BCLIBC_V3dT &BCLIBC_V3dT::operator*=(double scalar)
    {
        x *= scalar;
        y *= scalar;
        z *= scalar;
        return *this;
    }

    BCLIBC_V3dT &BCLIBC_V3dT::operator/=(double scalar)
    {
        if (std::fabs(scalar) < 1e-10)
        {
            return *this;
        }

        return (*this) *= (1.0 / scalar);
    }

    double BCLIBC_V3dT::mag() const
    {
        return std::sqrt((*this) * (*this));
    }

    BCLIBC_V3dT BCLIBC_V3dT::norm() const
    {
        double m = mag();
        if (std::fabs(m) < 1e-10)
        {
            return *this;
        }
        else
        {
            return (*this) * (1.0 / m);
        }
    }

    BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT &vec)
    {
        return vec * scalar;
    }
};