#include <cmath>
#include <cstddef>
#include "bclibc/interp.hpp"

namespace bclibc
{

    /**
     * @brief Returns the sign of a number.
     *
     * @param a Input value.
     * @return 1 if a > 0, -1 if a < 0, 0 if a == 0.
     */
    static inline int _sign(double a)
    {
        return (a > 0.0) - (a < 0.0);
    }

    /**
     * @brief Computes PCHIP slopes for three consecutive points.
     *
     * Calculates the monotone piecewise cubic Hermite slopes (m0, m1, m2)
     * for three points (x0, y0), (x1, y1), (x2, y2) suitable for PCHIP interpolation.
     *
     * @param x0 First point x-coordinate.
     * @param y0 First point y-coordinate.
     * @param x1 Second point x-coordinate.
     * @param y1 Second point y-coordinate.
     * @param x2 Third point x-coordinate.
     * @param y2 Third point y-coordinate.
     * @param m0 Output slope at first point.
     * @param m1 Output slope at second point (middle point).
     * @param m2 Output slope at third point.
     *
     * @note Assumes x0 < x1 < x2. Slopes are adjusted to preserve monotonicity.
     */
    static void BCLIBC_PchipSlopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                                    double &m0, double &m1, double &m2)
    {
        double h0 = x1 - x0;
        double h1 = x2 - x1;
        double d0 = (y1 - y0) / h0;
        double d1 = (y2 - y1) / h1;

        double h_sum = h0 + h1; // Calculate once

        // m1
        int s0 = _sign(d0);
        int s1 = _sign(d1);

        if (s0 * s1 <= 0)
        {
            m1 = 0.0;
        }
        else
        {
            double w1 = 2.0 * h1 + h0;
            double w2 = h1 + 2.0 * h0;
            m1 = (w1 + w2) / (w1 / d0 + w2 / d1);
        }

        // m0
        double m0l = ((2.0 * h0 + h1) * d0 - h0 * d1) / h_sum;
        if (s0 != _sign(m0l))
        {
            m0 = 0.0;
        }
        else
        {
            double abs_d0 = std::fabs(d0);
            m0 = (fabs(m0l) > 3.0 * abs_d0) ? 3.0 * d0 : m0l;
        }

        // m2
        double m2l = ((2.0 * h1 + h0) * d1 - h1 * d0) / h_sum;
        if (s1 != _sign(m2l))
        {
            m2 = 0.0;
        }
        else
        {
            double abs_d1 = std::fabs(d1);
            m2 = (fabs(m2l) > 3.0 * abs_d1) ? 3.0 * d1 : m2l;
        }
    }

    /**
     * @brief Evaluates a cubic Hermite polynomial at a given point.
     *
     * Uses Hermite basis functions to interpolate between two points with specified slopes.
     *
     * @param x Point at which to evaluate the polynomial.
     * @param xk Left point x-coordinate.
     * @param xk1 Right point x-coordinate.
     * @param yk Left point y-coordinate.
     * @param yk1 Right point y-coordinate.
     * @param mk Slope at left point.
     * @param mk1 Slope at right point.
     * @return Interpolated value at x.
     *
     * @note Uses Horner's scheme for numerical stability.
     */
    double BCLIBC_hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1)
    {
        // xk1 - xk
        double h = xk1 - xk;

        // (x - xk) / h
        double t = (x - xk) / h;

        // t * t
        double t2 = t * t;

        // t2 * t
        double t3 = t2 * t;

        // Use Horner scheme for better accuracy
        // H0(t) * yk
        double h00 = 2.0 * t3 - 3.0 * t2 + 1.0;
        // H1(t) * (mk * h)
        double h10 = (t - 2.0) * t2 + t;
        // H2(t) * yk1
        double h01 = -2.0 * t3 + 3.0 * t2;
        // H3(t) * (mk1 * h)
        double h11 = (t - 1.0) * t2;

        return h00 * yk + h * (h10 * mk + h11 * mk1) + h01 * yk1;
    }

    /**
     * @brief Performs 3-point monotone PCHIP interpolation.
     *
     * Interpolates the value at x using three support points (x0, y0), (x1, y1), (x2, y2).
     * Computes PCHIP slopes and evaluates the appropriate Hermite piece.
     *
     * @param x The x-coordinate at which to interpolate.
     * @param x0 First support point x-coordinate.
     * @param x1 Second support point x-coordinate.
     * @param x2 Third support point x-coordinate.
     * @param y0 First support point y-coordinate.
     * @param y1 Second support point y-coordinate.
     * @param y2 Third support point y-coordinate.
     * @return Interpolated y value at x.
     *
     * @note If x <= x1, interpolation occurs between first and second points,
     *       otherwise between second and third points.
     */
    double BCLIBC_interpolate3pt(double x, double x0, double x1, double x2, double y0, double y1, double y2)
    {

        // Sort without copying
        if (x1 < x0)
        {
            double t = x0;
            x0 = x1;
            x1 = t;
            t = y0;
            y0 = y1;
            y1 = t;
        }
        if (x2 < x1)
        {
            double tx = x2, ty = y2;
            if (x2 < x0)
            {
                x2 = x1;
                x1 = x0;
                x0 = tx;
                y2 = y1;
                y1 = y0;
                y0 = ty;
            }
            else
            {
                x2 = x1;
                x1 = tx;
                y2 = y1;
                y1 = ty;
            }
        }

        double m0, m1, m2;
        BCLIBC_PchipSlopes3(x0, y0, x1, y1, x2, y2, m0, m1, m2);

        return (x <= x1) ? BCLIBC_hermite(x, x0, x1, y0, y1, m0, m1)
                         : BCLIBC_hermite(x, x1, x2, y1, y2, m1, m2);
    }

    /**
     * @brief Performs linear interpolation between two points.
     *
     * Calculates y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
     *
     * @param x The x-coordinate at which to interpolate.
     * @param x0 First point x-coordinate.
     * @param y0 First point y-coordinate.
     * @param x1 Second point x-coordinate.
     * @param y1 Second point y-coordinate.
     * @param result Output parameter to store interpolated value.
     * @return BCLIBC_InterpStatus::SUCCESS on success,
     *         BCLIBC_InterpStatus::ZERODIVISION if x0 == x1.
     */
    BCLIBC_InterpStatus BCLIBC_interpolate2pt(double x, double x0, double y0, double x1, double y1, double &result)
    {
        if (x1 == x0)
        {
            return BCLIBC_InterpStatus::ZERODIVISION;
        }
        result = y0 + (y1 - y0) * (x - x0) / (x1 - x0);
        return BCLIBC_InterpStatus::SUCCESS;
    }
}; // namespace bclibc
