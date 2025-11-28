#ifndef BCLIBC_INTERP_HPP
#define BCLIBC_INTERP_HPP

namespace bclibc
{
    enum class BCLIBC_InterpStatus
    {
        SUCCESS,
        ZERODIVISION,
    };

    enum class BCLIBC_InterpMethod
    {
        PCHIP,
        LINEAR,
    };

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
    double BCLIBC_hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);

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
    double BCLIBC_interpolate3pt(double x, double x0, double x1, double x2, double y0, double y1, double y2);

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
    BCLIBC_InterpStatus BCLIBC_interpolate2pt(double x, double x0, double y0, double x1, double y1, double &result);

}; // namespace bclibc

#endif // BCLIBC_INTERP_HPP
