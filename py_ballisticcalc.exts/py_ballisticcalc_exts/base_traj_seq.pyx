# cython: freethreading_compatible=True
"""
Low-level, high-performance trajectory buffer and interpolation helpers (Cython).

This module provides:
- BaseTrajSeqT: a contiguous C buffer of BaseTraj_t items with append/reserve access.
- Monotone-preserving PCHIP (cubic Hermite) interpolation on the raw buffer without
    allocating Python objects.
- Convenience methods to locate and interpolate a point by an independent variable
    (time, mach, position.{x,y,z}, velocity.{x,y,z}) and slant_height.

Design note: nogil helpers operate on a tiny C struct view of the sequence to avoid
passing Python cdef-class instances into nogil code paths.
"""

from libc.math cimport cos, sin, fabs
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.interp cimport interpolate_3_pt


__all__ = ('BaseTrajSeqT')


cdef InterpKey _attribute_to_key(str key_attribute):
    cdef InterpKey key_kind

    if key_attribute == 'time':
        key_kind = KEY_TIME
    elif key_attribute == 'mach':
        key_kind = KEY_MACH
    elif key_attribute == 'position.x':
        key_kind = KEY_POS_X
    elif key_attribute == 'position.y':
        key_kind = KEY_POS_Y
    elif key_attribute == 'position.z':
        key_kind = KEY_POS_Z
    elif key_attribute == 'velocity.x':
        key_kind = KEY_VEL_X
    elif key_attribute == 'velocity.y':
        key_kind = KEY_VEL_Y
    elif key_attribute == 'velocity.z':
        key_kind = KEY_VEL_Z
    else:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

    return key_kind


cdef str _key_to_attribute(InterpKey key_kind):
    cdef str key_attribute
    
    if key_kind == KEY_TIME:
        key_attribute = 'time'
    elif key_kind == KEY_MACH:
        key_attribute = 'mach'
    elif key_kind == KEY_POS_X:
        key_attribute = 'position.x'
    elif key_kind == KEY_POS_Y:
        key_attribute = 'position.y'
    elif key_kind == KEY_POS_Z:
        key_attribute = 'position.z'
    elif key_kind == KEY_VEL_X:
        key_attribute = 'velocity.x'
    elif key_kind == KEY_VEL_Y:
        key_attribute = 'velocity.y'
    elif key_kind == KEY_VEL_Z:
        key_attribute = 'velocity.z'
    else:
        raise ValueError(f"Unknown InterpKey value: {key_kind}")
        
    return key_attribute


cdef class BaseTrajSeqT:
    """Contiguous C buffer of BaseTraj_t points with fast append and interpolation.

    Python-facing access lazily creates lightweight BaseTrajDataT objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        self._c_view = BaseTrajSeq_t_create()
        if self._c_view is NULL:
            raise MemoryError("Failed to create BaseTrajSeq_t")
    
    def __dealloc__(self):
        cdef BaseTrajSeq_t* ptr = self._c_view
        if ptr is not NULL:
            self._c_view = NULL
            BaseTrajSeq_t_destroy(ptr)
        
    cdef void _ensure_capacity_c(self, size_t min_capacity):
        cdef int ret = BaseTrajSeq_t_ensure_capacity(self._c_view, min_capacity)
        if ret < 0:
            raise MemoryError("Failed to allocate memory for trajectory buffer")

    cdef void _append_c(self, double time, double px, double py, double pz,
                        double vx, double vy, double vz, double mach):
        cdef int ret = BaseTrajSeq_t_append(self._c_view, time, px, py, pz, vx, vy, vz, mach)
        if ret < 0:
            raise MemoryError("Failed to allocate memory for trajectory buffer")

    def _ensure_capacity(self, size_t min_capacity):
        self._ensure_capacity_c(min_capacity)

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        self._append_c(time, px, py, pz, vx, vy, vz, mach)

    def reserve(self, Py_ssize_t min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")
        self._ensure_capacity_c(min_capacity)

    cdef BaseTraj_t* c_getitem(self, Py_ssize_t idx):
        cdef BaseTraj_t *item = BaseTrajSeq_t_get_item(self._c_view, idx)
        if item is NULL:
            raise IndexError("Index out of range")
        return item

    def __len__(self):
        """Number of points in the sequence."""
        return self.len_c()

    cdef Py_ssize_t len_c(self):
        cdef Py_ssize_t length = BaseTrajSeq_t_len(self._c_view)
        if length < 0:
            raise MemoryError("Trajectory buffer is NULL")
        return length 

    def __getitem__(self, idx: int) -> BaseTrajDataT:
        """Return BaseTrajDataT for the given index.  Supports negative indices."""
        cdef Py_ssize_t _i = <Py_ssize_t>idx
        cdef BaseTraj_t* entry_ptr = self.c_getitem(_i)
        cdef V3dT position = V3dT(
            entry_ptr.px,
            entry_ptr.py,
            entry_ptr.pz
        )
        cdef V3dT velocity = V3dT(
            entry_ptr.vx,
            entry_ptr.vy,
            entry_ptr.vz
        )
        return BaseTrajDataT(entry_ptr.time, position, velocity, entry_ptr.mach)

    cdef BaseTrajDataT _interpolate_at_c(self, Py_ssize_t idx, InterpKey key_kind, double key_value):
        """
        Interpolate at idx using points (idx-1, idx, idx+1) keyed by key_kind at key_value.
            Supports negative idx (which references from end of sequence).
        """
        cdef BaseTraj_t output
        cdef int ret = BaseTrajSeq_t_interpolate_raw(self._c_view, idx, key_kind, key_value, &output)
        
        if ret < 0:
            raise IndexError("interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)")

        cdef V3dT position = V3dT(output.px, output.py, output.pz)
        cdef V3dT velocity = V3dT(output.vx, output.vy, output.vz)

        return BaseTrajDataT(output.time, position, velocity, output.mach)

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        cdef InterpKey key_kind = _attribute_to_key(key_attribute)
        return self._interpolate_at_c(idx, key_kind, key_value)

    def get_at(self, str key_attribute, double key_value, object start_from_time=None) -> BaseTrajDataT:
        cdef InterpKey key_kind = _attribute_to_key(key_attribute)
        return self._get_at_c(key_kind, key_value, start_from_time)

    cdef BaseTrajDataT _get_at_c(self, InterpKey key_kind, double key_value, object start_from_time=None):
        """Get BaseTrajDataT where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """

        cdef Py_ssize_t n
        cdef BaseTraj_t* buf
        cdef Py_ssize_t i
        cdef Py_ssize_t start_idx
        cdef Py_ssize_t target_idx
        cdef Py_ssize_t center_idx
        cdef double sft
        cdef double epsilon
        cdef double curr_val
        cdef double next_val
        cdef double a
        cdef double b
        cdef double a2
        cdef double b2
        cdef bint search_forward

        n = <Py_ssize_t>self._c_view.length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")

        # If start_from_time is provided, mimic HitResult.get_at search strategy
        sft = 0.0
        if start_from_time is not None:
            sft = <double>start_from_time
        if sft > 0.0 and key_kind != KEY_TIME:
            buf = self._c_view.buffer
            start_idx = <Py_ssize_t>0
            # find first index with time >= start_from_time
            i = <Py_ssize_t>0
            while i < n:
                if buf[i].time >= sft:
                    start_idx = i
                    break
                i += 1
            epsilon = 1e-9
            curr_val = BaseTraj_t_key_val_from_kind_buf(&buf[start_idx], key_kind)
            if fabs(curr_val - key_value) < epsilon:
                return self[start_idx]
            search_forward = <bint>1
            if start_idx == n - 1:
                search_forward = <bint>0
            elif 0 < start_idx < n - 1:
                next_val = BaseTraj_t_key_val_from_kind_buf(&buf[start_idx + 1], key_kind)
                if (next_val > curr_val and key_value > curr_val) or (next_val < curr_val and key_value < curr_val):
                    search_forward = <bint>1
                else:
                    search_forward = <bint>0

            target_idx = <Py_ssize_t>(-1)
            if search_forward:
                i = <Py_ssize_t>start_idx
                while i < n - 1:
                    a = BaseTraj_t_key_val_from_kind_buf(&buf[i], key_kind)
                    b = BaseTraj_t_key_val_from_kind_buf(&buf[i + 1], key_kind)
                    if ((a < key_value <= b) or (b <= key_value < a)):
                        target_idx = i + 1
                        break
                    i += 1
            if target_idx == <Py_ssize_t>(-1):
                i = <Py_ssize_t>start_idx
                while i > 0:
                    a2 = BaseTraj_t_key_val_from_kind_buf(&buf[i], key_kind)
                    b2 = BaseTraj_t_key_val_from_kind_buf(&buf[i - 1], key_kind)
                    if ((b2 <= key_value < a2) or (a2 < key_value <= b2)):
                        target_idx = i
                        break
                    i -= 1
            if target_idx == <Py_ssize_t>(-1):
                raise ArithmeticError(f"Trajectory does not reach {_key_to_attribute(key_kind)} = {key_value}")
            if fabs(BaseTraj_t_key_val_from_kind_buf(&buf[target_idx], key_kind) - key_value) < epsilon:
                return self[target_idx]
            if target_idx == 0:
                target_idx = <Py_ssize_t>1
            center_idx = target_idx if target_idx < n - 1 else n - 2
            return self._interpolate_at_c(center_idx, key_kind, key_value)

        # Default: bisect across entire range
        cdef Py_ssize_t center = BaseTrajSeq_t_bisect_center_idx_buf(self._c_view, key_kind, key_value)
        if center < 0:
            raise ValueError("Interpolation requires at least 3 points")
        return self._interpolate_at_c(center, key_kind, key_value)

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get BaseTrajDataT where value == slant_height === position.y*cos(a) - position.x*sin(a)."""
        cdef double ca = cos(look_angle_rad)
        cdef double sa = sin(look_angle_rad)
        cdef Py_ssize_t n = <Py_ssize_t>self._c_view.length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")
        cdef Py_ssize_t center = BaseTrajSeq_t_bisect_center_idx_slant_buf(self._c_view, ca, sa, value)
        # Use three consecutive points around center to perform monotone PCHIP interpolation keyed on slant height
        cdef BaseTraj_t* buf = self._c_view.buffer
        cdef BaseTraj_t* p0 = &buf[center - 1]
        cdef BaseTraj_t* p1 = &buf[center]
        cdef BaseTraj_t* p2 = &buf[center + 1]
        cdef double ox0, ox1, ox2
        ox0 = BaseTraj_t_slant_val_buf(p0, ca, sa)
        ox1 = BaseTraj_t_slant_val_buf(p1, ca, sa)
        ox2 = BaseTraj_t_slant_val_buf(p2, ca, sa)
        if ox0 == ox1 or ox0 == ox2 or ox1 == ox2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        cdef double time = interpolate_3_pt(value, ox0, ox1, ox2, p0.time, p1.time, p2.time)
        cdef V3dT position = V3dT(
            interpolate_3_pt(value, ox0, ox1, ox2, p0.px, p1.px, p2.px),
            interpolate_3_pt(value, ox0, ox1, ox2, p0.py, p1.py, p2.py),
            interpolate_3_pt(value, ox0, ox1, ox2, p0.pz, p1.pz, p2.pz)
        )
        cdef V3dT velocity = V3dT(
            interpolate_3_pt(value, ox0, ox1, ox2, p0.vx, p1.vx, p2.vx),
            interpolate_3_pt(value, ox0, ox1, ox2, p0.vy, p1.vy, p2.vy),
            interpolate_3_pt(value, ox0, ox1, ox2, p0.vz, p1.vz, p2.vz)
        )
        cdef double mach = interpolate_3_pt(value, ox0, ox1, ox2, p0.mach, p1.mach, p2.mach)

        return BaseTrajDataT(time, position, velocity, mach)
