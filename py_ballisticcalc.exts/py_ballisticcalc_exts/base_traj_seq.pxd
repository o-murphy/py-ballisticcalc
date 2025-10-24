"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT, BaseTrajData_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport InterpKey, ErrorCode


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

    ctypedef struct BaseTrajSeq_t:
        BaseTraj_t* buffer
        size_t length
        size_t capacity

    ErrorCode BaseTrajSeq_t_interpolate_at(
        const BaseTrajSeq_t *seq,
        ssize_t idx,
        InterpKey key_kind,
        double key_value,
        BaseTrajData_t *out
    ) noexcept nogil

    void BaseTrajSeq_t_init(BaseTrajSeq_t *seq) noexcept nogil
    void BaseTrajSeq_t_release(BaseTrajSeq_t *seq) noexcept nogil

    Py_ssize_t BaseTrajSeq_t_len(BaseTrajSeq_t *seq) noexcept nogil
    BaseTraj_t* BaseTrajSeq_t_get_raw_item(BaseTrajSeq_t *seq, Py_ssize_t idx) noexcept nogil
    ErrorCode BaseTrajSeq_t_ensure_capacity(BaseTrajSeq_t *seq, size_t min_capacity) noexcept nogil
    ErrorCode BaseTrajSeq_t_append(
        BaseTrajSeq_t *seq,
        double time,
        double px,
        double py,
        double pz,
        double vx,
        double vy,
        double vz,
        double mach
    ) noexcept nogil
    ErrorCode BaseTrajSeq_t_get_at_slant_height(
        const BaseTrajSeq_t *seq,
        double look_angle_rad,
        double value,
        BaseTrajData_t *out
    ) noexcept nogil
    ErrorCode BaseTrajSeq_t_get_item(
        const BaseTrajSeq_t *seq,
        ssize_t idx, BaseTrajData_t *out
    ) noexcept nogil
    ErrorCode BaseTrajSeq_t_get_at(
        const BaseTrajSeq_t *seq,
        InterpKey key_kind,
        double key_value,
        double start_from_time,
        BaseTrajData_t *out
    ) noexcept nogil


cdef class BaseTrajSeqT:
    cdef BaseTrajSeq_t _c_view
