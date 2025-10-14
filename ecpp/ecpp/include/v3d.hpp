#pragma once

#include <iostream>
#include <cmath>

/**
 * @brief Class representing a 3D vector (x, y, z).
 * Designed to be immutable for binary arithmetic operations, returning new V3d objects.
 */
class V3d {
public:
    // Components are public and constant to enforce immutability
    double x, y, z; 

    // Default constructor (initializes to zero)
    V3d() : x(0.0), y(0.0), z(0.0) {}

    /**
     * @brief Component constructor.
     * Corresponds to the original `vec` function.
     */
    V3d(double x_val, double y_val, double z_val) 
        : x(x_val), y(y_val), z(z_val) {}

    // --- Unary Operator ---

    /**
     * @brief Unary minus (negation).
     * @return A new negated vector. (Immutable)
     */
    V3d operator-() const;

    // --- Binary Arithmetic Operators (Immutable) ---

    /**
     * @brief Vector addition.
     * @return A new vector (sum).
     */
    V3d operator+(const V3d& other) const;

    /**
     * @brief Vector subtraction.
     * @return A new vector (difference).
     */
    V3d operator-(const V3d& other) const;

    /**
     * @brief Scalar multiplication (Vector * Scalar).
     * @return A new vector scaled by the scalar.
     */
    V3d operator*(double scalar) const;

    /**
     * @brief Scalar division (Vector / Scalar).
     * @return A new vector divided by the scalar.
     */
    V3d operator/(double scalar) const;

    // --- Vector Algebra Methods ---

    /**
     * @brief Computes the dot product.
     * @return The scalar dot product.
     */
    double dot(const V3d& other) const;

    /**
     * @brief Computes the magnitude (length) of the vector.
     * @return The magnitude.
     */
    double mag() const;

    /**
     * @brief Returns a new normalized vector.
     * @return A new normalized V3d object. (Immutable)
     */
    V3d norm() const;
};

/**
 * @brief Scalar multiplication (Scalar * Vector).
 * Allows for commutative multiplication.
 */
V3d operator*(double scalar, const V3d& vec);

/**
 * @brief Overloads the stream insertion operator for easy printing.
 */
std::ostream& operator<<(std::ostream& os, const V3d& v);