// interp.h (Виправлено)
#ifndef INTERP_H
#define INTERP_H

#include <stddef.h>
#include <math.h>

#define INTERP_SUCCESS 0
#define INTERP_ERROR_ZERODIVISION -1

// Internal helpers for PCHIP
int _sign(double a);
void _sort3(double* xs, double* ys);
void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                    double* m0, double* m1, double* m2);
double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);

// Interpolation functions
double _interpolate_3_pt(double x, double x0, double y0, double x1, double y1, double x2, double y2);

// New: Declaration for 2-point interpolation
int _interpolate_2_pt(double x, double x0, double y0, double x1, double y1, double* result);

#endif /* INTERP_H */