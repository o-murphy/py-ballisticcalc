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

from libc.stdlib cimport realloc
from libc.stddef cimport size_t
from libc.math cimport cos, sin, fabs
from libc.string cimport memcpy
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from py_ballisticcalc_exts.trajectory_data cimport BaseTrajDataT, BaseTrajDataT_create
from py_ballisticcalc_exts.v3d cimport V3dT
from py_ballisticcalc_exts.trajectory_data cimport _sort3, _pchip_slopes3, _hermite

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

cdef enum InterpKey:
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

__all__ = ['CBaseTrajSeq', 'BaseTrajC']

cdef inline double _key_val_from_kind_buf(BaseTrajC* p, int key_kind) noexcept nogil:
    if key_kind == <int>KEY_TIME:
        return p.time
    elif key_kind == <int>KEY_MACH:
        return p.mach
    elif key_kind == <int>KEY_POS_X:
        return p.px
    elif key_kind == <int>KEY_POS_Y:
        return p.py
    elif key_kind == <int>KEY_POS_Z:
        return p.pz
    elif key_kind == <int>KEY_VEL_X:
        return p.vx
    elif key_kind == <int>KEY_VEL_Y:
        return p.vy
    elif key_kind == <int>KEY_VEL_Z:
        return p.vz
    return <double>0.0


# Interpolation helper (pure C math; safe to call with or without GIL)
cdef int _interpolate_nogil_raw(_CBaseTrajSeq_cview* seq, Py_ssize_t idx, int key_kind, double key_value, BaseTrajC* out) noexcept nogil:
    """Interpolate at idx using points (idx-1, idx, idx+1) where key equals key_value.

    Uses monotone-preserving PCHIP with Hermite evaluation; returns 1 on success, 0 on failure.
    """
    cdef BaseTrajC* buffer = seq._buffer
    cdef Py_ssize_t plength = <Py_ssize_t> seq._length
    cdef BaseTrajC *p0
    cdef BaseTrajC *p1
    cdef BaseTrajC *p2
    cdef double ox[3]
    cdef double xs[3]
    cdef double ys[3]
    cdef double m0 = 0.0
    cdef double m1 = 0.0
    cdef double m2 = 0.0
    cdef double x = key_value
    cdef double time, px, py, pz, vx, vy, vz, mach

    if idx < 0:
        idx += plength
    if idx <= 0 or idx >= plength - 1:
        return 0

    p0 = <BaseTrajC*>((<char*>buffer) + <size_t>(idx - 1) * sizeof(BaseTrajC))
    p1 = <BaseTrajC*>((<char*>buffer) + <size_t>idx * sizeof(BaseTrajC))
    p2 = <BaseTrajC*>((<char*>buffer) + <size_t>(idx + 1) * sizeof(BaseTrajC))

    if key_kind == <int>KEY_TIME:
        ox[0] = p0.time; ox[1] = p1.time; ox[2] = p2.time
    elif key_kind == <int>KEY_MACH:
        ox[0] = p0.mach; ox[1] = p1.mach; ox[2] = p2.mach
    elif key_kind == <int>KEY_POS_X:
        ox[0] = p0.px; ox[1] = p1.px; ox[2] = p2.px
    elif key_kind == <int>KEY_POS_Y:
        ox[0] = p0.py; ox[1] = p1.py; ox[2] = p2.py
    elif key_kind == <int>KEY_POS_Z:
        ox[0] = p0.pz; ox[1] = p1.pz; ox[2] = p2.pz
    elif key_kind == <int>KEY_VEL_X:
        ox[0] = p0.vx; ox[1] = p1.vx; ox[2] = p2.vx
    elif key_kind == <int>KEY_VEL_Y:
        ox[0] = p0.vy; ox[1] = p1.vy; ox[2] = p2.vy
    elif key_kind == <int>KEY_VEL_Z:
        ox[0] = p0.vz; ox[1] = p1.vz; ox[2] = p2.vz
    else:
        return 0

    if ox[0] == ox[1] or ox[0] == ox[2] or ox[1] == ox[2]:
        return 0

    if key_kind == <int>KEY_TIME:
        time = x
    else:
        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.time; ys[1] = p1.time; ys[2] = p2.time
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if x <= xs[1]:
            time = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            time = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.px; ys[1] = p1.px; ys[2] = p2.px
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        px = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        px = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.py; ys[1] = p1.py; ys[2] = p2.py
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        py = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        py = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.pz; ys[1] = p1.pz; ys[2] = p2.pz
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        pz = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        pz = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.vx; ys[1] = p1.vx; ys[2] = p2.vx
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        vx = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        vx = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.vy; ys[1] = p1.vy; ys[2] = p2.vy
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        vy = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        vy = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
    ys[0] = p0.vz; ys[1] = p1.vz; ys[2] = p2.vz
    _sort3(&xs[0], &ys[0])
    _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
    if x <= xs[1]:
        vz = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
    else:
        vz = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    if key_kind == <int>KEY_MACH:
        mach = x
    else:
        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.mach; ys[1] = p1.mach; ys[2] = p2.mach
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if x <= xs[1]:
            mach = _hermite(x, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            mach = _hermite(x, xs[1], xs[2], ys[1], ys[2], m1, m2)

    out.time = time
    out.px = px; out.py = py; out.pz = pz
    out.vx = vx; out.vy = vy; out.vz = vz
    out.mach = mach
    return 1


cdef inline double _slant_val_buf(BaseTrajC* p, double ca, double sa) noexcept nogil:
    """Computes the slant_height of a trajectory point `p` given cosine `ca` and sine `sa` of look_angle."""
    return p.py * ca - p.px * sa

cdef Py_ssize_t _bisect_center_idx_buf(BaseTrajC* buf, size_t length, int key_kind, double key_value) noexcept nogil:
    cdef Py_ssize_t n = <Py_ssize_t>length
    if n < 3:
        return <Py_ssize_t>(-1)
    cdef double v0 = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>0 * <size_t>sizeof(BaseTrajC)), key_kind)
    cdef double vN = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>(n - 1) * <size_t>sizeof(BaseTrajC)), key_kind)
    cdef int increasing = 1 if vN >= v0 else 0
    cdef Py_ssize_t lo = <Py_ssize_t>0
    cdef Py_ssize_t hi = n - 1
    cdef Py_ssize_t mid
    cdef double vm
    while lo < hi:
        mid = lo + ((hi - lo) >> 1)
        vm = _key_val_from_kind_buf(<BaseTrajC*>(<char*>buf + <size_t>mid * <size_t>sizeof(BaseTrajC)), key_kind)
        if increasing:
            if vm < key_value:
                lo = mid + 1
            else:
                hi = mid
        else:
            if vm > key_value:
                lo = mid + 1
            else:
                hi = mid
    if lo < 1:
        return <Py_ssize_t>1
    if lo > n - 2:
        return n - 2
    return lo

cdef Py_ssize_t _bisect_center_idx_slant_buf(BaseTrajC* buf, size_t length, double ca, double sa, double value) noexcept nogil:
    cdef Py_ssize_t n = <Py_ssize_t>length
    if n < 3:
        return <Py_ssize_t>(-1)
    cdef double v0 = _slant_val_buf(<BaseTrajC*>(<char*>buf + <size_t>0 * <size_t>sizeof(BaseTrajC)), ca, sa)
    cdef double vN = _slant_val_buf(<BaseTrajC*>(<char*>buf + <size_t>(n - 1) * <size_t>sizeof(BaseTrajC)), ca, sa)
    cdef int increasing = 1 if vN >= v0 else 0
    cdef Py_ssize_t lo = <Py_ssize_t>0
    cdef Py_ssize_t hi = n - 1
    cdef Py_ssize_t mid
    cdef double vm
    while lo < hi:
        mid = lo + ((hi - lo) >> 1)
        vm = _slant_val_buf(<BaseTrajC*>(<char*>buf + <size_t>mid * <size_t>sizeof(BaseTrajC)), ca, sa)
        if increasing:
            if vm < value:
                lo = mid + 1
            else:
                hi = mid
        else:
            if vm > value:
                lo = mid + 1
            else:
                hi = mid
    if lo < 1:
        return <Py_ssize_t>1
    if lo > n - 2:
        return n - 2
    return lo


cdef class CBaseTrajSeq:
    """Contiguous C buffer of BaseTrajC points with fast append and interpolation.

    Python-facing access lazily creates lightweight BaseTrajDataT objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        self._buffer = <BaseTrajC*>NULL
        self._length = <size_t>0
        self._capacity = <size_t>0

    def __dealloc__(self):
        if self._buffer:
            PyMem_Free(<void*>self._buffer)
            self._buffer = <BaseTrajC*>NULL

    cdef void _ensure_capacity(self, size_t min_capacity):
        cdef size_t new_capacity
        cdef BaseTrajC* new_buffer
        cdef size_t bytes_copy
        cdef size_t new_bytes
        if min_capacity > self._capacity:
            if self._capacity > 0:
                new_capacity = <size_t>(self._capacity * 2)
                if new_capacity < min_capacity:
                    new_capacity = min_capacity
            else:
                new_capacity = <size_t>16
                if new_capacity < min_capacity:
                    new_capacity = min_capacity
            new_bytes = (<size_t>new_capacity) * (<size_t>sizeof(BaseTrajC))
            new_buffer = <BaseTrajC*>PyMem_Malloc(<size_t>new_bytes)
            if not new_buffer:
                raise MemoryError("Failed to allocate memory for trajectory buffer")
            if self._buffer:
                if self._length:
                    bytes_copy = (<size_t>self._length) * (<size_t>sizeof(BaseTrajC))
                    memcpy(<void*>new_buffer, <const void*>self._buffer, <size_t>bytes_copy)
                PyMem_Free(<void*>self._buffer)
            self._buffer = new_buffer
            self._capacity = new_capacity

    cdef void _append_c(self, double time, double px, double py, double pz,
                        double vx, double vy, double vz, double mach):
        self._ensure_capacity(self._length + 1)
        cdef BaseTrajC* entry_ptr = <BaseTrajC*>(<char*>self._buffer + (<size_t>self._length) * (<size_t>sizeof(BaseTrajC)))
        entry_ptr.time = time
        entry_ptr.px = px; entry_ptr.py = py; entry_ptr.pz = pz
        entry_ptr.vx = vx; entry_ptr.vy = vy; entry_ptr.vz = vz
        entry_ptr.mach = mach
        self._length += 1

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        self._append_c(time, px, py, pz, vx, vy, vz, mach)

    def reserve(self, Py_ssize_t min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")
        self._ensure_capacity(<size_t>min_capacity)

    cdef BaseTrajC* c_getitem(self, Py_ssize_t idx):
        cdef Py_ssize_t length = <Py_ssize_t> self._length
        if idx < 0:
            idx += length
        if idx < 0 or idx >= length:
            raise IndexError("Index out of range")
        return <BaseTrajC*>(<char*>self._buffer + (<size_t>idx * <size_t>sizeof(BaseTrajC)))

    def __len__(self):
        """Number of points in the sequence."""
        return <Py_ssize_t> self._length

    def __getitem__(self, idx: int) -> BaseTrajDataT:
        """Return BaseTrajDataT for the given index.  Supports negative indices."""
        cdef V3dT position
        cdef V3dT velocity
        cdef BaseTrajC* entry_ptr
        cdef Py_ssize_t _i = <Py_ssize_t> idx
        entry_ptr = self.c_getitem(_i)
        position.x = entry_ptr.px; position.y = entry_ptr.py; position.z = entry_ptr.pz
        velocity.x = entry_ptr.vx; velocity.y = entry_ptr.vy; velocity.z = entry_ptr.vz
        return BaseTrajDataT_create(entry_ptr.time, position, velocity, entry_ptr.mach)


    cdef BaseTrajDataT _interpolate_at_c(self, Py_ssize_t idx, str key_attribute, double key_value):
        """
        Interpolate at idx using points (idx-1, idx, idx+1) keyed by key_kind at key_value.
            Supports negative idx (which references from end of sequence).
        """
        cdef BaseTrajC outp
        cdef V3dT pos
        cdef V3dT vel
        cdef BaseTrajDataT result
        cdef int key_kind

        if key_attribute == 'time':
            key_kind = <int>KEY_TIME
        elif key_attribute == 'mach':
            key_kind = <int>KEY_MACH
        elif key_attribute == 'position.x':
            key_kind = <int>KEY_POS_X
        elif key_attribute == 'position.y':
            key_kind = <int>KEY_POS_Y
        elif key_attribute == 'position.z':
            key_kind = <int>KEY_POS_Z
        elif key_attribute == 'velocity.x':
            key_kind = <int>KEY_VEL_X
        elif key_attribute == 'velocity.y':
            key_kind = <int>KEY_VEL_Y
        elif key_attribute == 'velocity.z':
            key_kind = <int>KEY_VEL_Z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        cdef Py_ssize_t _idx = idx
        if _idx < 0:
            _idx += <Py_ssize_t>self._length
        if _idx < 1:
            _idx += 1  # try to advance index so that we have a point to the left
        if _idx >= (<Py_ssize_t>self._length - 1):
            _idx -= 1  # try to retreat index so that we have a point to the right
        if _idx < 1:
            raise IndexError("interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)")

        cdef _CBaseTrajSeq_cview view
        view._buffer = self._buffer
        view._length = self._length
        view._capacity = self._capacity
        if not _interpolate_nogil_raw(&view, _idx, key_kind, key_value, &outp):
            raise IndexError("interpolate_at requires idx with valid neighbors (idx-1, idx, idx+1)")

        pos.x = outp.px; pos.y = outp.py; pos.z = outp.pz
        vel.x = outp.vx; vel.y = outp.vy; vel.z = outp.vz
        result = BaseTrajDataT_create(outp.time, pos, vel, outp.mach)
        return result

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        return self._interpolate_at_c(idx, key_attribute, key_value)

    def get_at(self, str key_attribute, double key_value, start_from_time=None):
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
            key_kind = <int>KEY_TIME
        elif key_attribute == 'mach':
            key_kind = <int>KEY_MACH
        elif key_attribute == 'position.x':
            key_kind = <int>KEY_POS_X
        elif key_attribute == 'position.y':
            key_kind = <int>KEY_POS_Y
        elif key_attribute == 'position.z':
            key_kind = <int>KEY_POS_Z
        elif key_attribute == 'velocity.x':
            key_kind = <int>KEY_VEL_X
        elif key_attribute == 'velocity.y':
            key_kind = <int>KEY_VEL_Y
        elif key_attribute == 'velocity.z':
            key_kind = <int>KEY_VEL_Z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        n = <Py_ssize_t>self._length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")

        # If start_from_time is provided, mimic HitResult.get_at search strategy
        sft = <double>0.0
        if start_from_time is not None:
            sft = <double>float(start_from_time)
        if sft > <double>0.0 and key_kind != <int>KEY_TIME:
            buf = self._buffer
            start_idx = <Py_ssize_t>0
            # find first index with time >= start_from_time
            i = <Py_ssize_t>0
            while i < n:
                if (<BaseTrajC*>(<char*>buf + <size_t>i * <size_t>sizeof(BaseTrajC))).time >= sft:
                    start_idx = i
                    break
                i += 1
            epsilon = <double>1e-9
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
        cdef Py_ssize_t center = _bisect_center_idx_buf(self._buffer, self._length, key_kind, key_value)
        if center < 0:
            raise ValueError("Interpolation requires at least 3 points")
        return self._interpolate_at_c(center, key_attribute, key_value)

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get BaseTrajDataT where value == slant_height === position.y*cos(a) - position.x*sin(a)."""
        cdef double ca = cos(look_angle_rad)
        cdef double sa = sin(look_angle_rad)
        cdef Py_ssize_t n = <Py_ssize_t>self._length
        if n < 3:
            raise ValueError("Interpolation requires at least 3 points")
        cdef Py_ssize_t center = _bisect_center_idx_slant_buf(self._buffer, self._length, ca, sa, value)
        # Use three consecutive points around center to perform monotone PCHIP interpolation keyed on slant height
        cdef BaseTrajC* buf = self._buffer
        cdef BaseTrajC* p0 = <BaseTrajC*>(<char*>buf + <size_t>(center - 1) * <size_t>sizeof(BaseTrajC))
        cdef BaseTrajC* p1 = <BaseTrajC*>(<char*>buf + <size_t>center * <size_t>sizeof(BaseTrajC))
        cdef BaseTrajC* p2 = <BaseTrajC*>(<char*>buf + <size_t>(center + 1) * <size_t>sizeof(BaseTrajC))
        cdef double ox[3]
        cdef double xs[3]
        cdef double ys[3]
        cdef double m0, m1, m2
        cdef V3dT pos
        cdef V3dT vel
        cdef double time
        cdef double mach

        ox[0] = _slant_val_buf(p0, ca, sa)
        ox[1] = _slant_val_buf(p1, ca, sa)
        ox[2] = _slant_val_buf(p2, ca, sa)
        if ox[0] == ox[1] or ox[0] == ox[2] or ox[1] == ox[2]:
            raise ZeroDivisionError("Duplicate x for interpolation")

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.time; ys[1] = p1.time; ys[2] = p2.time
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            time = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            time = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.px; ys[1] = p1.px; ys[2] = p2.px
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            pos.x = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            pos.x = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.py; ys[1] = p1.py; ys[2] = p2.py
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            pos.y = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            pos.y = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.pz; ys[1] = p1.pz; ys[2] = p2.pz
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            pos.z = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            pos.z = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.vx; ys[1] = p1.vx; ys[2] = p2.vx
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            vel.x = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            vel.x = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.vy; ys[1] = p1.vy; ys[2] = p2.vy
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            vel.y = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            vel.y = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.vz; ys[1] = p1.vz; ys[2] = p2.vz
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            vel.z = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            vel.z = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        xs[0] = ox[0]; xs[1] = ox[1]; xs[2] = ox[2]
        ys[0] = p0.mach; ys[1] = p1.mach; ys[2] = p2.mach
        _sort3(&xs[0], &ys[0])
        _pchip_slopes3(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2], &m0, &m1, &m2)
        if value <= xs[1]:
            mach = _hermite(value, xs[0], xs[1], ys[0], ys[1], m0, m1)
        else:
            mach = _hermite(value, xs[1], xs[2], ys[1], ys[2], m1, m2)

        return BaseTrajDataT_create(time, pos, vel, mach)
