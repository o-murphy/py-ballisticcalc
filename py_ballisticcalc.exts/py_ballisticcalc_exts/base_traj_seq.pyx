# cython: freethreading_compatible=True
"""
Low-level, high-performance trajectory buffer and interpolation helpers (Cython).

This module provides:
- BaseTrajSeqT: a contiguous C buffer of BCLIBC_BaseTraj items with append/reserve access.
- Monotone-preserving PCHIP (cubic Hermite) interpolation on the raw buffer without
    allocating Python objects.
- Convenience methods to locate and interpolate a point by an independent variable
    (time, mach, position.{x,y,z}, velocity.{x,y,z}) and slant_height.

Design note: nogil helpers operate on a tiny C struct view of the sequence to avoid
passing Python cdef-class instances into nogil code paths.
"""

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_BaseTrajData,
    BCLIBC_BaseTrajSeq_InterpKey,
    BCLIBC_ErrorType,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bind cimport _attribute_to_key, _key_to_attribute

__all__ = ('BaseTrajSeqT')


cdef class BaseTrajSeqT:
    """Contiguous C buffer of BCLIBC_BaseTraj points with fast append and interpolation.

    Python-facing access lazily creates lightweight BaseTrajDataT objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        BCLIBC_BaseTrajSeq_init(&self._c_view)

    def __dealloc__(self):
        BCLIBC_BaseTrajSeq_release(&self._c_view)

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_append(&self._c_view, time, px, py, pz, vx, vy, vz, mach)
        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return
        if err == BCLIBC_ErrorType.BCLIBC_E_MEMORY_ERROR:
            raise MemoryError("Failed to (re)allocate memory for trajectory buffer")
        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError('Invalid BCLIBC_BaseTrajSeq_append input')
        raise RuntimeError(f"undefined error occured during BCLIBC_BaseTrajSeq_append, error code: {err}")

    def reserve(self, int min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_ensureCapacity(&self._c_view, <Py_ssize_t>min_capacity)
        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return
        if err == BCLIBC_ErrorType.BCLIBC_E_MEMORY_ERROR:
            raise MemoryError("Failed to (re)allocate memory for trajectory buffer")
        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError('Invalid BCLIBC_BaseTrajSeq_ensureCapacity input')
        raise RuntimeError(
            f"undefined error occured during BCLIBC_BaseTrajSeq_ensureCapacity, error code: {err}"
        )

    def __len__(self):
        """Number of points in the sequence."""
        cdef Py_ssize_t length = BCLIBC_BaseTrajSeq_len(&self._c_view)
        if length < 0:
            raise MemoryError("Trajectory buffer is NULL")
        return <int>length

    def __getitem__(self, idx: int) -> BaseTrajDataT:
        """Return BaseTrajDataT for the given index.  Supports negative indices."""
        cdef Py_ssize_t _i = <Py_ssize_t>idx
        cdef BCLIBC_BaseTrajData out
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_getItem(&self._c_view, _i, &out)
        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return BaseTrajDataT(out)
        raise IndexError("Index out of range")

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        cdef BCLIBC_BaseTrajSeq_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef BCLIBC_BaseTrajData output
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_interpolateAt(
            &self._c_view, idx, key_kind, key_value, &output
        )

        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return BaseTrajDataT(output)

        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError("invalid BCLIBC_BaseTrajSeq_interpolateAt input")
        if err == BCLIBC_ErrorType.BCLIBC_E_INDEX_ERROR:
            raise IndexError(
                "BCLIBC_BaseTrajSeq_interpolateAt requires idx with valid neighbors (idx-1, idx, idx+1)"
            )
        if err == BCLIBC_ErrorType.BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR:
            raise AttributeError("invalid BCLIBC_BaseTrajSeq_InterpKey")
        raise RuntimeError(
            f"undefined error occured during BCLIBC_BaseTrajSeq_interpolateAt, error code: {err}"
        )

    def get_at(self, str key_attribute, double key_value, object start_from_time=None) -> BaseTrajDataT:
        """Get BaseTrajDataT where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """
        cdef BCLIBC_BaseTrajSeq_InterpKey key_kind = _attribute_to_key(key_attribute)

        cdef BCLIBC_BaseTrajData out
        cdef double _start_from_time = 0.0
        if start_from_time is not None:
            _start_from_time = <double>start_from_time
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_getAt(
            &self._c_view, key_kind, key_value, _start_from_time, &out
        )
        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return BaseTrajDataT(out)

        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError("Interpolation requires at least 3 points")
        if err == BCLIBC_ErrorType.BCLIBC_E_ARITHMETIC_ERROR:
            raise ArithmeticError(
                f"Trajectory does not reach {_key_to_attribute(key_kind)} = {key_value}")
        raise RuntimeError(f"undefined internal error in BCLIBC_BaseTrajSeq_getAt, error code: {err}")

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get BaseTrajDataT where value == slant_height === position.y*cos(a) - position.x*sin(a)."""

        cdef BCLIBC_BaseTrajData out
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajSeq_getAtSlantHeight(&self._c_view, look_angle_rad, value, &out)
        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return BaseTrajDataT(out)

        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError("Interpolation requires at least 3 points")
        if err == BCLIBC_ErrorType.BCLIBC_E_ZERO_DIVISION_ERROR:
            raise ZeroDivisionError("Duplicate x for interpolation")
        raise RuntimeError(f"undefined error in BCLIBC_BaseTrajSeq_getAtSlantHeight, error code: {err}")
