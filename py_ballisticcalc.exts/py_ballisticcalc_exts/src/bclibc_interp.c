#include <math.h>
#include <stddef.h>
#include "bclibc_interp.h"

// Internal helpers for PCHIP
static inline int _sign(double a)
{
    return (a > 0.0) - (a < 0.0);
}

// Internal helpers for PCHIP used by bclibc_base_traj_seq
static void BCLIBC_Sort3(double *xs, double *ys)
{
    // Sort the first two elements
    if (xs[1] < xs[0])
    {
        double tx = xs[0];
        xs[0] = xs[1];
        xs[1] = tx;
        double ty = ys[0];
        ys[0] = ys[1];
        ys[1] = ty;
    }
    // Insert the third element in the correct position
    if (xs[2] < xs[1])
    {
        double tx = xs[2];
        double ty = ys[2];
        if (xs[2] < xs[0])
        {
            xs[2] = xs[1];
            xs[1] = xs[0];
            xs[0] = tx;
            ys[2] = ys[1];
            ys[1] = ys[0];
            ys[0] = ty;
        }
        else
        {
            xs[2] = xs[1];
            xs[1] = tx;
            ys[2] = ys[1];
            ys[1] = ty;
        }
    }
}

static void BCLIBC_PchipSlopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                                double *m0, double *m1, double *m2)
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
        *m1 = 0.0;
    }
    else
    {
        double w1 = 2.0 * h1 + h0;
        double w2 = h1 + 2.0 * h0;
        *m1 = (w1 + w2) / (w1 / d0 + w2 / d1);
    }

    // m0
    double m0l = ((2.0 * h0 + h1) * d0 - h0 * d1) / h_sum;
    if (s0 != _sign(m0l))
    {
        *m0 = 0.0;
    }
    else
    {
        double abs_d0 = fabs(d0);
        *m0 = (fabs(m0l) > 3.0 * abs_d0) ? 3.0 * d0 : m0l;
    }

    // m2
    double m2l = ((2.0 * h1 + h0) * d1 - h1 * d0) / h_sum;
    if (s1 != _sign(m2l))
    {
        *m2 = 0.0;
    }
    else
    {
        double abs_d1 = fabs(d1);
        *m2 = (fabs(m2l) > 3.0 * abs_d1) ? 3.0 * d1 : m2l;
    }
}

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

// Interpolation functions
// Monotone PCHIP interpolation for a single component using 3 support points.
// Sorts (x*, y*) by x*, computes PCHIP slopes, and evaluates the Hermite piece
// containing x. Assumes all x* distinct. Returns interpolated y.
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
    BCLIBC_PchipSlopes3(x0, y0, x1, y1, x2, y2, &m0, &m1, &m2);

    return (x <= x1) ? BCLIBC_hermite(x, x0, x1, y0, y1, m0, m1)
                     : BCLIBC_hermite(x, x1, x2, y1, y2, m1, m2);
}

// Declaration for 2-point interpolation
int BCLIBC_interpolate2pt(double x, double x0, double y0, double x1, double y1, double *result)
{
    if (x1 == x0)
    {
        return BCLIBC_INTERP_ERROR_ZERODIVISION;
    }
    *result = y0 + (y1 - y0) * (x - x0) / (x1 - x0);
    return BCLIBC_INTERP_SUCCESS;
}
