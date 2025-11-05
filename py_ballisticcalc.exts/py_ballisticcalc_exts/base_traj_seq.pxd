"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_BaseTrajSeq_InterpKey,
    BCLIBC_BaseTrajData,
    BCLIBC_ErrorType,
)

cdef extern from "include/bclibc_base_traj_seq.h" nogil:
    ctypedef struct BCLIBC_BaseTraj:
        double time
        double px
        double py
        double pz
        double vx
        double vy
        double vz
        double mach

    ctypedef struct BCLIBC_BaseTrajSeq:
        BCLIBC_BaseTraj* buffer
        size_t length
        size_t capacity

    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_interpolateAt(
        const BCLIBC_BaseTrajSeq *seq,
        ssize_t idx,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil

    void BCLIBC_BaseTrajSeq_init(BCLIBC_BaseTrajSeq *seq) noexcept nogil
    void BCLIBC_BaseTrajSeq_release(BCLIBC_BaseTrajSeq *seq) noexcept nogil

    Py_ssize_t BCLIBC_BaseTrajSeq_len(BCLIBC_BaseTrajSeq *seq) noexcept nogil
    BCLIBC_BaseTraj* BCLIBC_BaseTrajSeq_getRawItem(BCLIBC_BaseTrajSeq *seq, Py_ssize_t idx) noexcept nogil
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_ensureCapacity(BCLIBC_BaseTrajSeq *seq, size_t min_capacity) noexcept nogil
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_append(
        BCLIBC_BaseTrajSeq *seq,
        double time,
        double px,
        double py,
        double pz,
        double vx,
        double vy,
        double vz,
        double mach
    ) noexcept nogil
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAtSlantHeight(
        const BCLIBC_BaseTrajSeq *seq,
        double look_angle_rad,
        double value,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getItem(
        const BCLIBC_BaseTrajSeq *seq,
        ssize_t idx, BCLIBC_BaseTrajData *out
    ) noexcept nogil
    BCLIBC_ErrorType BCLIBC_BaseTrajSeq_getAt(
        const BCLIBC_BaseTrajSeq *seq,
        BCLIBC_BaseTrajSeq_InterpKey key_kind,
        double key_value,
        double start_from_time,
        BCLIBC_BaseTrajData *out
    ) noexcept nogil


cdef class BaseTrajSeqT:
    cdef BCLIBC_BaseTrajSeq _c_view
