"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT

cdef extern from "include/base_traj_seq.h" nogil:
    ctypedef struct BaseTraj_t:
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

    ctypedef struct BaseTrajSeq_t:
        BaseTraj_t* buffer
        size_t length
        size_t capacity

    double BaseTraj_t_key_val_from_kind_buf(const BaseTraj_t* p, InterpKey key_kind) noexcept nogil
    double BaseTraj_t_slant_val_buf(const BaseTraj_t* p, double ca, double sa) noexcept nogil

    int BaseTrajSeq_t_interpolate_raw(
        const BaseTrajSeq_t* seq,
        Py_ssize_t idx,
        InterpKey key_kind,
        double key_value,
        BaseTraj_t* out
    ) except? 0 nogil

    BaseTrajSeq_t* BaseTrajSeq_t_create() noexcept nogil
    void BaseTrajSeq_t_destroy(BaseTrajSeq_t *seq) noexcept nogil
    Py_ssize_t BaseTrajSeq_t_len(BaseTrajSeq_t *seq) noexcept nogil
    BaseTraj_t* BaseTrajSeq_t_get_item(BaseTrajSeq_t *seq, Py_ssize_t idx) noexcept nogil
    int BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity) noexcept nogil
    int BaseTrajSeq_t_append(BaseTrajSeq_t *seq, double time, double px, double py, double pz, double vx, double vy, double vz, double mach) noexcept nogil
    Py_ssize_t BaseTrajSeq_t_bisect_center_idx_buf(
        const BaseTrajSeq_t* seq,
        InterpKey key_kind,
        double key_value
    ) noexcept nogil
    Py_ssize_t BaseTrajSeq_t_bisect_center_idx_slant_buf(
        const BaseTrajSeq_t* seq,
        double ca,
        double sa,
        double value
    ) noexcept nogil


cdef InterpKey _attribute_to_key(str key_attribute)
cdef str _key_to_attribute(InterpKey key_kind)


cdef class BaseTrajSeqT:
    cdef BaseTrajSeq_t* _c_view

    cdef void _ensure_capacity_c(self, size_t min_capacity)
    cdef void _append_c(self, double time, double px, double py, double pz,
            double vx, double vy, double vz, double mach)
    cdef Py_ssize_t len_c(self)
    cdef BaseTraj_t* c_getitem(self, Py_ssize_t idx)
    cdef BaseTrajDataT _get_at_c(self, InterpKey key_kind, double key_value, object start_from_time = *)
    cdef BaseTrajDataT _interpolate_at_c(self, Py_ssize_t idx, InterpKey key_kind, double key_value)
