// interp.h (Виправлено)
#ifndef BCLIB_INTERP_H
#define BCLIB_INTERP_H

#define INTERP_SUCCESS 0
#define INTERP_ERROR_ZERODIVISION -1

#ifdef __cplusplus
extern "C"
{
#endif

    double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);

    // Interpolation functions
    // Monotone PCHIP interpolation for a single component using 3 support points.
    // Sorts (x*, y*) by x*, computes PCHIP slopes, and evaluates the Hermite piece
    // containing x. Assumes all x* distinct. Returns interpolated y.
    double interpolate_3_pt(double x, double x0, double x1, double x2, double y0, double y1, double y2);

    // Declaration for 2-point interpolation
    int interpolate_2_pt(double x, double x0, double y0, double x1, double y1, double *result);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_INTERP_H
