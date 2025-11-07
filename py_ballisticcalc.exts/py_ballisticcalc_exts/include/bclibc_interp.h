#ifndef BCLIBC_INTERP_H
#define BCLIBC_INTERP_H

#define BCLIBC_INTERP_SUCCESS 0
#define BCLIBC_INTERP_ERROR_ZERODIVISION -1

typedef enum {
    BCLIBC_INTERP_METHOD_PCHIP,
    BCLIBC_INTERP_METHOD_LINEAR,
} BCLIBC_InterpMethod;

#ifdef __cplusplus
extern "C"
{
#endif

    double BCLIBC_hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);

    // Interpolation functions
    // Monotone PCHIP interpolation for a single component using 3 support points.
    // Sorts (x*, y*) by x*, computes PCHIP slopes, and evaluates the Hermite piece
    // containing x. Assumes all x* distinct. Returns interpolated y.
    double BCLIBC_interpolate3pt(double x, double x0, double x1, double x2, double y0, double y1, double y2);

    // Declaration for 2-point interpolation
    int BCLIBC_interpolate2pt(double x, double x0, double y0, double x1, double y1, double *result);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_INTERP_H
