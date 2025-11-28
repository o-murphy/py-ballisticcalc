cdef extern from "include/bclibc/interp.hpp" namespace "bclibc" nogil:
    cdef int BCLIBC_INTERP_ERROR_ZERODIVISION

    cdef enum class BCLIBC_InterpStatus:
        SUCCESS
        ZERODIVISION

    cdef enum class BCLIBC_InterpMethod:
        PCHIP
        LINEAR

    # Internal nogil helpers for PCHIP used by traj_data
    double BCLIBC_hermite(
        double x, double xk, double xk1, double yk, double yk1, double mk, double mk1
    ) noexcept nogil

    # Internal nogil helpers for PCHIP used by traj_data
    double BCLIBC_interpolate3pt(
        double x, double x0, double x1, double x2,
        double y0, double y1, double y2
    ) noexcept nogil
    BCLIBC_InterpStatus BCLIBC_interpolate2pt(
        double x, double x0, double y0,
        double x1, double y1, double &result
    ) noexcept nogil
