# cython: freethreading_compatible=True

from libcpp.vector cimport vector
from libc.stddef cimport ptrdiff_t
from py_ballisticcalc_exts.traj_data cimport BCLIBC_TrajectoryData

cdef list get_records(const vector[BCLIBC_TrajectoryData] *records)

cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
