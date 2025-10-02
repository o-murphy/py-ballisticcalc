// interp.h (Виправлено)
#ifndef INTERP_H
#define INTERP_H

#define INTERP_SUCCESS 0
#define INTERP_ERROR_ZERODIVISION -1

int _sign(double a);

// Internal helpers for PCHIP used by base_traj_seq
void _sort3(double* xs, double* ys);

void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                                  double* m0, double* m1, double* m2);

double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1);


// Interpolation functions
// Monotone PCHIP interpolation for a single component using 3 support points.
// Sorts (x*, y*) by x*, computes PCHIP slopes, and evaluates the Hermite piece
// containing x. Assumes all x* distinct. Returns interpolated y.
double _interpolate_3_pt(double x, double x0, double x1, double x2, double y0, double y1, double y2);


// Declaration for 2-point interpolation
int _interpolate_2_pt(double x, double x0, double y0, double x1, double y1, double* result);

#endif /* INTERP_H */