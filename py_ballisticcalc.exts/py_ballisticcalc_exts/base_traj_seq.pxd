"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

from libc.stddef cimport size_t
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT

cdef extern from "include/basetraj_seq.h" nogil:
    ctypedef struct BaseTrajC:
        double time
        double px
        double py
        double pz
        double vx
        double vy
        double vz
        double mach

cdef class CBaseTrajSeq:
  cdef:
    BaseTrajC* _buffer
    size_t _length
    size_t _capacity
  cdef void _ensure_capacity(self, size_t min_capacity)
  cdef void _append_c(self, double time, double px, double py, double pz,
            double vx, double vy, double vz, double mach)
  cdef BaseTrajC* c_getitem(self, Py_ssize_t idx)
  cdef BaseTrajDataT _interpolate_at_c(self, Py_ssize_t idx, str key_attribute, double key_value)
