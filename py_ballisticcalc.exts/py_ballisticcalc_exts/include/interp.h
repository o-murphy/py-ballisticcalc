// interp.h (Виправлено)
#ifndef INTERP_H
#define INTERP_H

#include <stddef.h>
#include <math.h>

#define INTERP_SUCCESS 0
#define INTERP_ERROR_ZERODIVISION -1

// // Internal helpers for PCHIP
// int _sign(double a);
// void _sort3(double* xs, double* ys);
// void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
//                     double* m0, double* m1, double* m2);
// double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);

static inline int _sign(double a) {
    return (a > 0.0) ? 1 : ((a < 0.0) ? -1 : 0);
}

// Internal helpers for PCHIP used by base_traj_seq
static inline void _sort3(double* xs, double* ys) {
    int i, j, min_idx;
    double tx, ty;

    for (i = 0; i < 2; i++) {
        min_idx = i;

        for (j = i + 1; j < 3; j++) {
            if (xs[j] < xs[min_idx]) {
                min_idx = j;
            }
        }

        if (min_idx != i) {
            tx = xs[i];
            xs[i] = xs[min_idx];
            xs[min_idx] = tx;

            ty = ys[i];
            ys[i] = ys[min_idx];
            ys[min_idx] = ty;
        }
    }
}

static inline void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                                  double* m0, double* m1, double* m2) {
    double h0 = x1 - x0;
    double h1 = x2 - x1;

    double d0 = (y1 - y0) / h0;
    double d1 = (y2 - y1) / h1;

    double m1l;
    double w1;
    double w2;
    double m0l;
    double m2l;

    if (_sign(d0) * _sign(d1) <= 0) {
        m1l = 0.0;
    } else {
        w1 = 2.0 * h1 + h0;
        w2 = h1 + 2.0 * h0;
        // (w1 + w2) / (w1/d0 + w2/d1)
        m1l = (w1 + w2) / (w1 / d0 + w2 / d1);
    }

    m0l = ((2.0 * h0 + h1) * d0 - h0 * d1) / (h0 + h1);

    if (_sign(m0l) != _sign(d0)) {
        m0l = 0.0;
    }
    else if (fabs(m0l) > 3.0 * fabs(d0)) {
        m0l = 3.0 * d0;
    }

    m2l = ((2.0 * h1 + h0) * d1 - h1 * d0) / (h0 + h1);

    if (_sign(m2l) != _sign(d1)) {
        m2l = 0.0;
    }
    else if (fabs(m2l) > 3.0 * fabs(d1)) {
        m2l = 3.0 * d1;
    }

    m0[0] = m0l;
    m1[0] = m1l;
    m2[0] = m2l;
}

static inline double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1) {
    // xk1 - xk
    double h = xk1 - xk;

    // (x - xk) / h
    double t = (x - xk) / h;

    // t * t
    double t2 = t * t;

    // t2 * t
    double t3 = t2 * t;

    return (
        // H0(t) * yk
        (2.0 * t3 - 3.0 * t2 + 1.0) * yk

        // H1(t) * (mk * h)
        + (t3 - 2.0 * t2 + t) * (mk * h)

        // H2(t) * yk1
        + (-2.0 * t3 + 3.0 * t2) * yk1

        // H3(t) * (mk1 * h)
        + (t3 - t2) * (mk1 * h)
    );
}


// Interpolation functions
double _interpolate_3_pt(double x, double x0, double y0, double x1, double y1, double x2, double y2);

// New: Declaration for 2-point interpolation
int _interpolate_2_pt(double x, double x0, double y0, double x1, double y1, double* result);

#endif /* INTERP_H */