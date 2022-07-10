import cython
from cython.cimports.libc import math


def calculate_by_curve(data: list, curve: list, mach: float) -> cython.float:
    num_points: cython.int = len(curve)
    mlo: cython.int = 0
    mhi: cython.int = num_points - 2
    mid: cython.int

    while mhi - mlo > 1:
        mid = int(math.floor(mhi + mlo) / 2.0)
        if data[mid].a < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].a - mach > mach - data[mlo].a:
        m = mlo
    else:
        m = mhi
    return curve[m].c + mach * (curve[m].b + curve[m].a * mach)
