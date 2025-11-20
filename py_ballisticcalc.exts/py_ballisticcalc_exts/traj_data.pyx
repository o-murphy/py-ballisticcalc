# cython: freethreading_compatible=True
"""
Low-level, high-performance trajectory buffer and interpolation helpers (Cython).

This module provides:
- BaseTrajSeqT: a contiguous C buffer of BCLIBC_BaseTrajData items with append/reserve access.
- Monotone-preserving PCHIP (cubic Hermite) interpolation on the raw buffer without
    allocating Python objects.
- Convenience methods to locate and interpolate a point by an independent variable
    (time, mach, position.{x,y,z}, velocity.{x,y,z}) and slant_height.

Design note: nogil helpers operate on a tiny C struct view of the sequence to avoid
passing Python cdef-class instances into nogil code paths.
"""

from cython cimport final
from py_ballisticcalc_exts.base_types cimport BCLIBC_ErrorType
from py_ballisticcalc_exts.bind cimport _attribute_to_key, _key_to_attribute, v3d_to_vector

__all__ = ('BaseTrajSeqT')


@final
cdef class BaseTrajSeqT:
    """Contiguous C buffer of BCLIBC_BaseTrajData points with fast append and interpolation.

    Python-facing access lazily creates lightweight BaseTrajDataT objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        pass

    def __dealloc__(self):
        pass

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        cdef BCLIBC_ErrorType err = self._this.append(
            BCLIBC_BaseTrajData(time, px, py, pz, vx, vy, vz, mach)
        )
        if err == BCLIBC_ErrorType.NO_ERROR:
            return
        if err == BCLIBC_ErrorType.MEMORY_ERROR:
            raise MemoryError("Failed to (re)allocate memory for trajectory buffer")
        if err == BCLIBC_ErrorType.VALUE_ERROR:
            raise ValueError('Invalid BCLIBC_BaseTrajSeq.append input')
        raise RuntimeError(f"undefined error occured during BCLIBC_BaseTrajSeq.append, error code: {err}")

    def reserve(self, int min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        import warnings
        warnings.warn("reserve method deprecated due to auto resources manage")
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")

    def __len__(self):
        """Number of points in the sequence."""
        cdef Py_ssize_t length = self._this.get_length()
        if length < 0:
            raise MemoryError("Trajectory buffer is NULL")
        return <int>length

    def __getitem__(self, idx: int) -> BaseTrajDataT:
        """Return BaseTrajDataT for the given index.  Supports negative indices."""
        cdef Py_ssize_t _i = <Py_ssize_t>idx
        cdef BaseTrajDataT out = BaseTrajDataT()
        cdef BCLIBC_ErrorType err = self._this.get_item(_i, out._this)
        if err == BCLIBC_ErrorType.NO_ERROR:
            return out
        raise IndexError("Index out of range")

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef BaseTrajDataT out = BaseTrajDataT()
        cdef BCLIBC_ErrorType err = self._this.interpolate_at(
            idx, key_kind, key_value, out._this
        )

        if err == BCLIBC_ErrorType.NO_ERROR:
            return out

        if err == BCLIBC_ErrorType.VALUE_ERROR:
            raise ValueError("invalid BCLIBC_BaseTrajSeq.interpolate_at input")
        if err == BCLIBC_ErrorType.INDEX_ERROR:
            raise IndexError(
                "BCLIBC_BaseTrajSeq.interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)"
            )
        if err == BCLIBC_ErrorType.BASE_TRAJ_INTERP_KEY_ERROR:
            raise AttributeError("invalid BCLIBC_BaseTrajData_InterpKey")
        raise RuntimeError(
            f"undefined error occured during BCLIBC_BaseTrajSeq.interpolate_at, error code: {err}"
        )

    def get_at(self, str key_attribute, double key_value, object start_from_time=None) -> BaseTrajDataT:
        """Get BaseTrajDataT where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)

        cdef BaseTrajDataT out = BaseTrajDataT()
        cdef double _start_from_time = 0.0
        if start_from_time is not None:
            _start_from_time = <double>start_from_time
        cdef BCLIBC_ErrorType err = self._this.get_at(
            key_kind, key_value, _start_from_time, out._this
        )
        if err == BCLIBC_ErrorType.NO_ERROR:
            return out

        if err == BCLIBC_ErrorType.VALUE_ERROR:
            raise ValueError("Interpolation requires at least 3 points")
        if err == BCLIBC_ErrorType.ARITHMETIC_ERROR:
            raise ArithmeticError(
                f"Trajectory does not reach {_key_to_attribute(key_kind)} = {key_value}")
        raise RuntimeError(f"undefined internal error in BCLIBC_BaseTrajSeq.get_at, error code: {err}")

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get BaseTrajDataT where value == slant_height === position.y*cos(a) - position.x*sin(a)."""

        cdef BaseTrajDataT out = BaseTrajDataT()
        cdef BCLIBC_ErrorType err = self._this.get_at_slant_height(look_angle_rad, value, out._this)
        if err == BCLIBC_ErrorType.NO_ERROR:
            return out

        if err == BCLIBC_ErrorType.VALUE_ERROR:
            raise ValueError("Interpolation requires at least 3 points")
        if err == BCLIBC_ErrorType.ZERO_DIVISION_ERROR:
            raise ZeroDivisionError("Duplicate x for interpolation")
        raise RuntimeError(f"undefined error in BCLIBC_BaseTrajSeq.get_at_slant_height, error code: {err}")


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    @property
    def time(self):
        return self._this.time

    @property
    def mach(self):
        return self._this.mach

    # Python-facing properties return Vector, not dict
    @property
    def position(self):
        cdef BCLIBC_V3dT pos = self._this.position()
        return v3d_to_vector(&pos)

    @property
    def velocity(self):
        cdef BCLIBC_V3dT vel = self._this.velocity()
        return v3d_to_vector(&vel)

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                    BaseTrajDataT p0, BaseTrajDataT p1, BaseTrajDataT p2):
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation
        of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach',
                or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (BaseTrajDataT):
                Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef BaseTrajDataT out = BaseTrajDataT()
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajData.interpolate(
            key_kind, key_value,
            p0._this, p1._this, p2._this,
            out._this
        )

        if err == BCLIBC_ErrorType.NO_ERROR:
            return out

        if err == BCLIBC_ErrorType.VALUE_ERROR:
            raise ValueError("invalid BCLIBC_BaseTrajData.interpolate input")
        if err == BCLIBC_ErrorType.BASE_TRAJ_INTERP_KEY_ERROR:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        if err == BCLIBC_ErrorType.ZERO_DIVISION_ERROR:
            raise ZeroDivisionError("Duplicate x for interpolation")
        raise RuntimeError("unknown error in BCLIBC_BaseTrajData.interpolate")
