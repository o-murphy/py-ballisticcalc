"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

# noinspection PyUnresolvedReferences
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

    ctypedef enum InterpKey:
        KEY_TIME
        KEY_MACH
        KEY_POS_X
        KEY_POS_Y
        KEY_POS_Z
        KEY_VEL_X
        KEY_VEL_Y
        KEY_VEL_Z

    ctypedef struct _CBaseTrajSeq_cview:
        BaseTrajC* _buffer
        size_t _length
        size_t _capacity

    inline double _key_val_from_kind_buf(const BaseTrajC* p, int key_kind)
    inline double _slant_val_buf(const BaseTrajC* p, double ca, double sa)

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
