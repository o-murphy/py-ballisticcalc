#include "v3d.hpp"
#include <cmath>
#include <cstdio> // Required for std::fabs

// --- Unary Operators ---

V3d V3d::operator-() const {
    // Corresponds to neg
    return V3d(-x, -y, -z);
}

// --- Binary Arithmetic Operators (Immutable) ---

V3d V3d::operator+(const V3d& other) const {
    // Corresponds to add
    return V3d(x + other.x, y + other.y, z + other.z);
}

V3d V3d::operator-(const V3d& other) const {
    // Corresponds to sub
    return V3d(x - other.x, y - other.y, z - other.z);
}

V3d V3d::operator*(double scalar) const {
    // Corresponds to mulS
    return V3d(x * scalar, y * scalar, z * scalar);
}

V3d V3d::operator/(double scalar) const {
    if (std::fabs(scalar) < 1e-10) {
        // Return original or handle division by zero (e.g., throw exception).
        // Returning the original vector (or a copy) for safety.
        return *this; 
    }
    // Reuse the scalar multiplication operator
    return (*this) * (1.0 / scalar);
}

// --- Vector Algebra Methods ---

double V3d::dot(const V3d& other) const {
    // Corresponds to dot
    return (x * other.x) + (y * other.y) + (z * other.z);
}

double V3d::mag() const {
    // Corresponds to mag
    return std::sqrt(dot(*this));
}

V3d V3d::norm() const {
    // Corresponds to norm
    double m = mag();

    if (std::fabs(m) < 1e-10) {
        // Return a copy of the original if magnitude is near zero
        return *this;
    } else {
        // Reuse the scalar multiplication operator
        return (*this) * (1.0 / m);
    }
}

// --- Free Functions / Non-Member Operators ---

V3d operator*(double scalar, const V3d& vec) {
    // Allows for commutative multiplication: 5.0 * V.
    // Simply calls V.operator*(5.0)
    return vec * scalar; 
}

std::ostream& operator<<(std::ostream& os, const V3d& v) {
    // Provides functionality similar to print_vec
    os << "(" << v.x << ", " << v.y << ", " << v.z << ")";
    return os;
}