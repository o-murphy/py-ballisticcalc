cdef extern from "include/bclibc_interp.h" nogil:
    cdef int BCLIBC_INTERP_ERROR_ZERODIVISION

    ctypedef enum BCLIBC_InterpMethod:
        BCLIBC_INTERP_METHOD_PCHIP
        BCLIBC_INTERP_METHOD_LINEAR

    # Internal nogil helpers for PCHIP used by base_traj_seq
    double BCLIBC_hermite(
        double x, double xk, double xk1, double yk, double yk1, double mk, double mk1
    ) noexcept nogil

    # Internal nogil helpers for PCHIP used by base_traj_seq
    double BCLIBC_interpolate3pt(
        double x, double x0, double x1, double x2,
        double y0, double y1, double y2
    ) noexcept nogil
    int BCLIBC_interpolate2pt(
        double x, double x0, double y0,
        double x1, double y1, double * result
    ) except? -1 nogil
