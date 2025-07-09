#ifndef V3D_H
#define V3D_H

#include <cmath> // For std::sqrt, std::fabs
#include <iostream> // For std::cout

class V3d {
public:
    double x;
    double y;
    double z;

    // Constructors
    V3d(); // Default constructor
    V3d(double x_val, double y_val, double z_val); // Parameterized constructor

    // Member functions
    V3d operator+(const V3d& other) const; // Vector addition
    V3d operator-(const V3d& other) const; // Vector subtraction
    V3d operator-() const; // Unary negation
    V3d operator*(double scalar) const; // Scalar multiplication
    double dot(const V3d& other) const; // Dot product
    double mag() const; // Magnitude
    void normalize_inplace(); // Normalize in place
    V3d normalize() const; // Return a new normalized vector

    // Friend function for scalar multiplication (scalar * vector)
    friend V3d operator*(double scalar, const V3d& vec);

    // Print function
    void print(const char* name) const;
};

#endif // V3D_H