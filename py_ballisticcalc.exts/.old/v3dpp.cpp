#include "v3dpp.hpp"
#include <cmath> // Required for std::fabs and std::sqrt
#include <iostream> // Required for std::cout

// Default constructor
V3d::V3d() : x(0.0), y(0.0), z(0.0) {}

// Parameterized constructor
V3d::V3d(double x_val, double y_val, double z_val) : x(x_val), y(y_val), z(z_val) {}

// Vector addition
V3d V3d::operator+(const V3d& other) const {
    return V3d(x + other.x, y + other.y, z + other.z);
}

// Vector subtraction
V3d V3d::operator-(const V3d& other) const {
    return V3d(x - other.x, y - other.y, z - other.z);
}

// Unary negation
V3d V3d::operator-() const {
    return V3d(-x, -y, -z);
}

// Scalar multiplication (vector * scalar)
V3d V3d::operator*(double scalar) const {
    return V3d(x * scalar, y * scalar, z * scalar);
}

// Friend function for scalar multiplication (scalar * vector)
V3d operator*(double scalar, const V3d& vec) {
    return V3d(vec.x * scalar, vec.y * scalar, vec.z * scalar);
}

// Dot product
double V3d::dot(const V3d& other) const {
    return (x * other.x) + (y * other.y) + (z * other.z);
}

// Magnitude
double V3d::mag() const {
    return std::sqrt((x * x) + (y * y) + (z * z));
}

// Normalize in place
void V3d::normalize_inplace() {
    double m = mag();
    if (std::fabs(m) < 1e-10) {
        return; // Do nothing if magnitude is near zero
    } else {
        x /= m;
        y /= m;
        z /= m;
    }
}

// Return a new normalized vector
V3d V3d::normalize() const {
    double m = mag();
    if (std::fabs(m) < 1e-10) {
        return *this; // Return the original vector if magnitude is near zero
    } else {
        return V3d(x / m, y / m, z / m);
    }
}

// Print function
void V3d::print(const char* name) const {
    std::cout << name << " = (" << x << ", " << y << ", " << z << ")" << std::endl;
}