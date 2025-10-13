"""
Low-level, high-performance trajectory buffer and interpolation helpers (Cython).

This module provides:
- CBaseTrajSeq: a contiguous C buffer of BaseTrajC items with append/reserve access.
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
from py_ballisticcalc_exts.interp cimport _interpolate_3_pt
from py_ballisticcalc_exts.base_traj_seq cimport (BaseTrajC, CBaseTrajSeq_t, 
    KEY_TIME, KEY_MACH, KEY_POS_X, KEY_POS_Y, KEY_POS_Z, KEY_VEL_X, KEY_VEL_Y, KEY_VEL_Z, _key_val_from_kind_buf)


__all__ = ('CBaseTrajSeq', 'BaseTrajC')


cdef class CBaseTrajSeq:
    """Contiguous C buffer of BaseTrajC points with fast append and interpolation.

    Python-facing access lazily creates lightweight BaseTrajDataT objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        self._c_view = CBaseTrajSeq_t_create()
        if self._c_view is NULL:
            raise MemoryError("Failed to create CBaseTrajSeq_t")
    
    def __dealloc__(self):
        cdef CBaseTrajSeq_t* ptr = self._c_view
        if ptr is not NULL:
            self._c_view = NULL
            CBaseTrajSeq_t_destroy(ptr)
        
    cdef void _ensure_capacity_c(self, size_t min_capacity):
        cdef int ret = CBaseTrajSeq_t_ensure_capacity(self._c_view, min_capacity)
        if ret < 0:
            raise MemoryError("Failed to allocate memory for trajectory buffer")

    cdef void _append_c(self, double time, double px, double py, double pz,
                        double vx, double vy, double vz, double mach):
        cdef int ret = CBaseTrajSeq_t_append(self._c_view, time, px, py, pz, vx, vy, vz, mach)
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

    cdef BaseTrajC* c_getitem(self, Py_ssize_t idx):
        cdef BaseTrajC *item = CBaseTrajSeq_t_get_item(self._c_view, idx)
        if item == NULL:
            raise IndexError("Index out of range")
        return item

    def __len__(self):
        """Number of points in the sequence."""
        return <Py_ssize_t> self._c_view._length

    def __getitem__(self, idx: int) -> BaseTrajDataT:
        """Return BaseTrajDataT for the given index.  Supports negative indices."""
        cdef V3dT position
        cdef V3dT velocity
        cdef BaseTrajC* entry_ptr
        cdef Py_ssize_t _i = <Py_ssize_t>idx
        entry_ptr = self.c_getitem(_i)
        position.x = entry_ptr.px; position.y = entry_ptr.py; position.z = entry_ptr.pz
        velocity.x = entry_ptr.vx; velocity.y = entry_ptr.vy; velocity.z = entry_ptr.vz
        return BaseTrajDataT(entry_ptr.time, position, velocity, entry_ptr.mach)

    cdef BaseTrajDataT _interpolate_at_c(self, Py_ssize_t idx, str key_attribute, double key_value):
        """
        Interpolate at idx using points (idx-1, idx, idx+1) keyed by key_kind at key_value.
            Supports negative idx (which references from end of sequence).
        """
        cdef:
            BaseTrajC outp
            V3dT pos
            V3dT vel
            int key_kind

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

        cdef Py_ssize_t _idx = idx
        if _idx < 0:
            _idx += <Py_ssize_t>self._c_view._length
        if _idx < 1:
            _idx += 1  # try to advance index so that we have a point to the left
        if _idx >= (<Py_ssize_t>self._c_view._length - 1):
            _idx -= 1  # try to retreat index so that we have a point to the right
        if _idx < 1:
            raise IndexError("interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)")

        cdef CBaseTrajSeq_t view
        view._buffer = self._c_view._buffer
        view._length = self._c_view._length
        view._capacity = self._c_view._capacity
        if not _interpolate_raw(&view, _idx, key_kind, key_value, &outp):
            raise IndexError("interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)")

        pos.x = outp.px; pos.y = outp.py; pos.z = outp.pz
        vel.x = outp.vx; vel.y = outp.vy; vel.z = outp.vz
        return BaseTrajDataT(outp.time, pos, vel, outp.mach)

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        return self._interpolate_at_c(idx, key_attribute, key_value)

    def get_at(self, str key_attribute, double key_value, object start_from_time=None) -> BaseTrajDataT:
        return self._get_at_c(key_attribute, key_value, start_from_time)

    cdef BaseTrajDataT _get_at_c(self, str key_attribute, double key_value, object start_from_time=None):
        """Get BaseTrajDataT where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """
        cdef int key_kind
        cdef Py_ssize_t n
        cdef BaseTrajC* buf
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
        n = <Py_ssize_t>self._c_view._length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")

        # If start_from_time is provided, mimic HitResult.get_at search strategy
        sft = 0.0
        if start_from_time is not None:
            sft = start_from_time
        if sft > 0.0 and key_kind != KEY_TIME:
            buf = self._c_view._buffer
            start_idx = <Py_ssize_t>0
            # find first index with time >= start_from_time
            i = <Py_ssize_t>0
            while i < n:
                if (<BaseTrajC*>(<char*>buf + <size_t>i * <size_t>sizeof(BaseTrajC))).time >= sft:
                    start_idx = i
                    break
                i += 1
            epsilon = 1e-9
            curr_val = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>start_idx * <size_t>sizeof(BaseTrajC)), key_kind)
            if fabs(curr_val - key_value) < epsilon:
                return self[start_idx]
            search_forward = <bint>1
            if start_idx == n - 1:
                search_forward = <bint>0
            elif 0 < start_idx < n - 1:
                next_val = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>(start_idx + 1) * <size_t>sizeof(BaseTrajC)), key_kind)
                if (next_val > curr_val and key_value > curr_val) or (next_val < curr_val and key_value < curr_val):
                    search_forward = <bint>1
                else:
                    search_forward = <bint>0

            target_idx = <Py_ssize_t>(-1)
            if search_forward:
                i = <Py_ssize_t>start_idx
                while i < n - 1:
                    a = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>i * <size_t>sizeof(BaseTrajC)), key_kind)
                    b = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>(i + 1) * <size_t>sizeof(BaseTrajC)), key_kind)
                    if ((a < key_value <= b) or (b <= key_value < a)):
                        target_idx = i + 1
                        break
                    i += 1
            if target_idx == <Py_ssize_t>(-1):
                i = <Py_ssize_t>start_idx
                while i > 0:
                    a2 = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>i * <size_t>sizeof(BaseTrajC)), key_kind)
                    b2 = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>(i - 1) * <size_t>sizeof(BaseTrajC)), key_kind)
                    if ((b2 <= key_value < a2) or (a2 < key_value <= b2)):
                        target_idx = i
                        break
                    i -= 1
            if target_idx == <Py_ssize_t>(-1):
                raise ArithmeticError(f"Trajectory does not reach {key_attribute} = {key_value}")
            if fabs(_key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>target_idx * <size_t>sizeof(BaseTrajC)), key_kind) - key_value) < epsilon:
                return self[target_idx]
            if target_idx == 0:
                target_idx = <Py_ssize_t>1
            center_idx = target_idx if target_idx < n - 1 else n - 2
            return self._interpolate_at_c(center_idx, key_attribute, key_value)

        # Default: bisect across entire range
        cdef Py_ssize_t center = _bisect_center_idx_buf(self._c_view._buffer, self._c_view._length, key_kind, key_value)
        if center < 0:
            raise ValueError("Interpolation requires at least 3 points")
        return self._interpolate_at_c(center, key_attribute, key_value)

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get BaseTrajDataT where value == slant_height === position.y*cos(a) - position.x*sin(a)."""
        cdef double ca = cos(look_angle_rad)
        cdef double sa = sin(look_angle_rad)
        cdef Py_ssize_t n = <Py_ssize_t>self._c_view._length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")
        cdef Py_ssize_t center = _bisect_center_idx_slant_buf(self._c_view._buffer, self._c_view._length, ca, sa, value)
        # Use three consecutive points around center to perform monotone PCHIP interpolation keyed on slant height
        cdef BaseTrajC* buf = self._c_view._buffer
        cdef BaseTrajC* p0 = <BaseTrajC*>(<char*>buf + <size_t>(center - 1) * <size_t>sizeof(BaseTrajC))
        cdef BaseTrajC* p1 = <BaseTrajC*>(<char*>buf + <size_t>center * <size_t>sizeof(BaseTrajC))
        cdef BaseTrajC* p2 = <BaseTrajC*>(<char*>buf + <size_t>(center + 1) * <size_t>sizeof(BaseTrajC))
        cdef double ox0, ox1, ox2
        cdef V3dT pos
        cdef V3dT vel
        cdef double time
        cdef double mach
        ox0 = _slant_val_buf(p0, ca, sa)
        ox1 = _slant_val_buf(p1, ca, sa)
        ox2 = _slant_val_buf(p2, ca, sa)
        if ox0 == ox1 or ox0 == ox2 or ox1 == ox2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        time = _interpolate_3_pt(value, ox0, ox1, ox2, p0.time, p1.time, p2.time)
        pos.x = _interpolate_3_pt(value, ox0, ox1, ox2, p0.px, p1.px, p2.px)
        pos.y = _interpolate_3_pt(value, ox0, ox1, ox2, p0.py, p1.py, p2.py)
        pos.z = _interpolate_3_pt(value, ox0, ox1, ox2, p0.pz, p1.pz, p2.pz)
        vel.x = _interpolate_3_pt(value, ox0, ox1, ox2, p0.vx, p1.vx, p2.vx)
        vel.y = _interpolate_3_pt(value, ox0, ox1, ox2, p0.vy, p1.vy, p2.vy)
        vel.z = _interpolate_3_pt(value, ox0, ox1, ox2, p0.vz, p1.vz, p2.vz)
        mach = _interpolate_3_pt(value, ox0, ox1, ox2, p0.mach, p1.mach, p2.mach)

        return BaseTrajDataT(time, pos, vel, mach)
