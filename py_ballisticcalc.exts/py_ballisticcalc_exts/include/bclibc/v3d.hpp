#ifndef BCLIBC_V3dT_HPP
#define BCLIBC_V3dT_HPP

#include <cmath>

namespace bclibc
{

    // Structure definition for 3D vector
    struct BCLIBC_V3dT
    {
    public:
        double x;
        double y;
        double z;

        // ============================================================================
        // Constructors
        // ============================================================================

        BCLIBC_V3dT() = default;

        inline BCLIBC_V3dT(double x, double y, double z)
            : x(x), y(y), z(z) {}

        // ============================================================================
        // Arithmetic Operators (Create new vectors)
        // ============================================================================

        /**
         * @brief Adds two vectors component-wise.
         * @return New vector representing the sum.
         */
        inline BCLIBC_V3dT operator+(const BCLIBC_V3dT &other) const
        {
            return BCLIBC_V3dT(x + other.x, y + other.y, z + other.z);
        }

        /**
         * @brief Negates all vector components.
         * @return New vector with negated components.
         */
        inline BCLIBC_V3dT operator-() const
        {
            return BCLIBC_V3dT(-x, -y, -z);
        }

        /**
         * @brief Subtracts one vector from another component-wise.
         * @return New vector representing the difference.
         */
        inline BCLIBC_V3dT operator-(const BCLIBC_V3dT &other) const
        {
            return BCLIBC_V3dT(x - other.x, y - other.y, z - other.z);
        }

        /**
         * @brief Multiplies vector by a scalar.
         * @return New scaled vector.
         */
        inline BCLIBC_V3dT operator*(double scalar) const
        {
            return BCLIBC_V3dT(x * scalar, y * scalar, z * scalar);
        }

        /**
         * @brief Divides vector by a scalar.
         * @note Returns unchanged vector if scalar is near zero to avoid division by zero.
         * @return New scaled vector.
         */
        inline BCLIBC_V3dT operator/(double scalar) const
        {
            if (std::fabs(scalar) < 1e-10)
            {
                return *this;
            }
            // Use multiplication by reciprocal for better performance
            return (*this) * (1.0 / scalar);
        }

        /**
         * @brief Computes dot product of two vectors.
         * @return Scalar dot product value.
         */
        inline double operator*(const BCLIBC_V3dT &other) const
        {
            return (x * other.x) + (y * other.y) + (z * other.z);
        }

        // ============================================================================
        // Compound Assignment Operators (Modify in-place - FASTEST)
        // ============================================================================

        /**
         * @brief Adds another vector to this vector in-place.
         * @note Most efficient form for accumulation operations.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &operator+=(const BCLIBC_V3dT &other)
        {
            x += other.x;
            y += other.y;
            z += other.z;
            return *this;
        }

        /**
         * @brief Subtracts another vector from this vector in-place.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &operator-=(const BCLIBC_V3dT &other)
        {
            x -= other.x;
            y -= other.y;
            z -= other.z;
            return *this;
        }

        /**
         * @brief Scales this vector by a scalar in-place.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &operator*=(double scalar)
        {
            x *= scalar;
            y *= scalar;
            z *= scalar;
            return *this;
        }

        /**
         * @brief Divides this vector by a scalar in-place.
         * @note Returns unchanged if scalar is near zero.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &operator/=(double scalar)
        {
            if (std::fabs(scalar) < 1e-10)
            {
                return *this;
            }
            // Use multiplication by reciprocal
            return (*this) *= (1.0 / scalar);
        }

        // ============================================================================
        // Optimized Fused Operations (Avoid temporary allocations)
        // ============================================================================

        /**
         * @brief Fused multiply-add operation: this += other * scalar.
         *
         * Performs the operation in-place without creating temporary vectors.
         * This is significantly faster than: vec += other * scalar
         *
         * Use cases:
         * - RK4 integration: v_temp += k1_v * dt_half
         * - Weighted sums: result += component * weight
         *
         * @param other The vector to be scaled and added.
         * @param scalar The scaling factor.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &fused_multiply_add(const BCLIBC_V3dT &other, double scalar)
        {
            x += other.x * scalar;
            y += other.y * scalar;
            z += other.z * scalar;
            return *this;
        }

        /**
         * @brief Fused multiply-subtract operation: this -= other * scalar.
         *
         * Performs the operation in-place without creating temporary vectors.
         *
         * @param other The vector to be scaled and subtracted.
         * @param scalar The scaling factor.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &fused_multiply_subtract(const BCLIBC_V3dT &other, double scalar)
        {
            x -= other.x * scalar;
            y -= other.y * scalar;
            z -= other.z * scalar;
            return *this;
        }

        /**
         * @brief Computes linear combination: this = a * vec_a + b * vec_b.
         *
         * Highly optimized for RK4 integration where weighted sums are common.
         * Avoids all temporary allocations.
         *
         * Example: result.linear_combination(k1, 1.0, k2, 2.0)
         * This is faster than: result = k1 + k2 * 2.0
         *
         * @param vec_a First vector.
         * @param scalar_a Scaling factor for first vector.
         * @param vec_b Second vector.
         * @param scalar_b Scaling factor for second vector.
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &linear_combination(
            const BCLIBC_V3dT &vec_a, double scalar_a,
            const BCLIBC_V3dT &vec_b, double scalar_b)
        {
            x = vec_a.x * scalar_a + vec_b.x * scalar_b;
            y = vec_a.y * scalar_a + vec_b.y * scalar_b;
            z = vec_a.z * scalar_a + vec_b.z * scalar_b;
            return *this;
        }

        /**
         * @brief Computes 4-term linear combination: this = a*v_a + b*v_b + c*v_c + d*v_d.
         *
         * Optimized specifically for RK4 final step calculation:
         * result = (k1 + 2*k2 + 2*k3 + k4) / 6
         *
         * Can be called as: result.linear_combination_4(k1, 1.0, k2, 2.0, k3, 2.0, k4, 1.0)
         *
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &linear_combination_4(
            const BCLIBC_V3dT &v_a, double s_a,
            const BCLIBC_V3dT &v_b, double s_b,
            const BCLIBC_V3dT &v_c, double s_c,
            const BCLIBC_V3dT &v_d, double s_d)
        {
            x = v_a.x * s_a + v_b.x * s_b + v_c.x * s_c + v_d.x * s_d;
            y = v_a.y * s_a + v_b.y * s_b + v_c.y * s_c + v_d.y * s_d;
            z = v_a.z * s_a + v_b.z * s_b + v_c.z * s_c + v_d.z * s_d;
            return *this;
        }

        // ============================================================================
        // Vector Properties
        // ============================================================================

        /**
         * @brief Computes the magnitude (length) of the vector.
         *
         * Uses optimized sqrt(dot(v,v)) computation.
         *
         * @return The Euclidean length of the vector.
         */
        inline double mag() const
        {
            return std::sqrt((*this) * (*this));
        }

        /**
         * @brief Computes squared magnitude without taking square root.
         *
         * Much faster than mag() when you only need to compare lengths
         * or when the actual magnitude isn't needed.
         *
         * Use cases:
         * - Comparing distances: if (v.mag_squared() < threshold_squared)
         * - Computing kinetic energy: KE = 0.5 * mass * velocity.mag_squared()
         *
         * @return The squared Euclidean length.
         */
        inline double mag_squared() const
        {
            return (*this) * (*this);
        }

        /**
         * @brief Returns a normalized (unit length) version of this vector.
         *
         * Creates a new vector with the same direction but magnitude of 1.
         * Returns the original vector if magnitude is near zero to avoid division by zero.
         *
         * @return New unit vector in the same direction.
         */
        inline BCLIBC_V3dT norm() const
        {
            const double m_sq = x * x + y * y + z * z;
            if (m_sq < 1e-20)
            {
                return *this;
            }
            const double inv_mag = 1.0 / std::sqrt(m_sq);
            return BCLIBC_V3dT(x * inv_mag, y * inv_mag, z * inv_mag);
        }

        /**
         * @brief Normalizes this vector in-place.
         *
         * Modifies this vector to have unit length while preserving direction.
         * More efficient than creating a new normalized vector.
         *
         * @return Reference to this vector for chaining.
         */
        inline BCLIBC_V3dT &normalize()
        {
            const double m_sq = x * x + y * y + z * z;
            if (m_sq < 1e-20)
            {
                return *this;
            }
            const double inv_mag = 1.0 / std::sqrt(m_sq);
            x *= inv_mag;
            y *= inv_mag;
            z *= inv_mag;
            return *this;
        }
    };

    // ============================================================================
    // Non-member Functions
    // ============================================================================

    /**
     * @brief Allows scalar-vector multiplication in either order.
     *
     * Enables syntax: scalar * vector (in addition to vector * scalar)
     *
     * @param scalar The scaling factor.
     * @param vec The vector to scale.
     * @return New scaled vector.
     */
    inline BCLIBC_V3dT operator*(double scalar, const BCLIBC_V3dT &vec)
    {
        return vec * scalar;
    }

}; // namespace bclibc

#endif // BCLIBC_V3dT_HPP
