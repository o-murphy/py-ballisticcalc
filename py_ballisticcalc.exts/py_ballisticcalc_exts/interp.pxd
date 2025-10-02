cdef extern from "include/interp.h":
    cdef int INTERP_ERROR_ZERODIVISION

    # Internal nogil helpers for PCHIP used by base_traj_seq
    int _sign(double a) noexcept nogil
    void _sort3(double * xs, double * ys) noexcept nogil
    void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                        double * m0, double * m1, double * m2) noexcept nogil
    double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1) noexcept nogil

    # Internal nogil helpers for PCHIP used by base_traj_seq
    double _interpolate_3_pt(double x, double x0, double x1, double x2, double y0, double y1, double y2) noexcept nogil
    int _interpolate_2_pt(double x, double x0, double y0, double x1, double y1, double * result) except? -1 nogil
