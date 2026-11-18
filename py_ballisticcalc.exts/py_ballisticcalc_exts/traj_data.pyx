# cython: freethreading_compatible=True
"""
Low-level, high-performance trajectory buffer and interpolation helpers (Cython).

This module provides:
- CythonizedBaseTrajSeq: a contiguous C buffer of BCLIBC_BaseTrajData items with append/reserve access.
- Monotone-preserving PCHIP (cubic Hermite) interpolation on the raw buffer without
    allocating Python objects.
- Convenience methods to locate and interpolate a point by an independent variable
    (time, mach, position.{x,y,z}, velocity.{x,y,z}) and slant_height.

Design note: nogil helpers operate on a tiny C struct view of the sequence to avoid
passing Python cdef-class instances into nogil code paths.
"""

from cython cimport final
from py_ballisticcalc_exts.bind cimport _attribute_to_key, v3d_to_vector
from py_ballisticcalc_exts.result cimport BCLIBC_Result, monostate, raise_std_error
from libcpp.functional cimport reference_wrapper
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Energy, Unit, Velocity, Weight

cdef object _tuple_new = tuple.__new__
cdef object _obj_new = object.__new__
cdef object _TD = TrajectoryData
cdef object _Distance = Distance, _Velocity = Velocity, _Angular = Angular, _Energy = Energy, _Weight = Weight
cdef object _U_FOOT = Unit.Foot, _U_FPS = Unit.FPS, _U_RAD = Unit.Radian, _U_FTLB = Unit.FootPound, _U_LB = Unit.Pound
cdef dict _flags = {}


cdef inline object _feet(double v):
    d = _obj_new(_Distance)
    d._value = v * 12
    d._defined_units = _U_FOOT
    return d


cdef inline object _fps(double v):
    d = _obj_new(_Velocity)
    d._value = v / 3.2808399
    d._defined_units = _U_FPS
    return d


cdef inline object _rad(double v):
    d = _obj_new(_Angular)
    d._value = v
    d._defined_units = _U_RAD
    return d


cdef inline object _ft_lb(double v):
    d = _obj_new(_Energy)
    d._value = v
    d._defined_units = _U_FTLB
    return d


cdef inline object _lb(double v):
    d = _obj_new(_Weight)
    d._value = v / 0.000142857143
    d._defined_units = _U_LB
    return d

__all__ = ('CythonizedBaseTrajSeq', 'CythonizedBaseTrajData')


# @final is safe with abi3: no other Cython module subclasses this type.
# If you need to subclass it from another .pyx, remove @final — see engines.pyx for context.
@final
cdef class CythonizedBaseTrajSeq:
    """Contiguous C buffer of BCLIBC_BaseTrajData points with fast append and interpolation.

    Python-facing access lazily creates lightweight CythonizedBaseTrajData objects; internal
        nogil helpers work directly on the C buffer for speed.
    """
    def __cinit__(self):
        pass

    def __dealloc__(self):
        pass

    def append(self, double time, double px, double py, double pz,
               double vx, double vy, double vz, double mach):
        """Append a new point to the sequence."""
        self._this.append(
            BCLIBC_BaseTrajData(time, px, py, pz, vx, vy, vz, mach)
        )

    def reserve(self, int min_capacity):
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        import warnings
        warnings.warn("reserve method deprecated due to auto resources manage")
        if min_capacity < 0:
            raise ValueError("min_capacity must be non-negative")

    def __len__(self):
        """Number of points in the sequence."""
        cdef Py_ssize_t length = self._this.get_length()
        return <int>length

    def __getitem__(self, idx: int) -> CythonizedBaseTrajData:
        """Return CythonizedBaseTrajData for the given index.  Supports negative indices."""
        cdef Py_ssize_t _i = <Py_ssize_t>idx
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBC_Result[reference_wrapper[const BCLIBC_BaseTrajData]] item = self._this[_i]
        if not item.has_value():
            raise IndexError(item.error().what().decode("utf-8"))
        out._this = item.value().get()
        return out

    def interpolate_at(self, Py_ssize_t idx, str key_attribute, double key_value):
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBC_Result[monostate] res = self._this.interpolate_at(idx, key_kind, key_value, out._this)
        if not res.has_value():
            raise_std_error(res.error())
        return out

    def get_at(self, str key_attribute, double key_value, object start_from_time=None) -> CythonizedBaseTrajData:
        """Get CythonizedBaseTrajData where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef double _start_from_time = 0.0
        if start_from_time is not None:
            _start_from_time = <double>start_from_time
        cdef BCLIBC_Result[monostate] res = self._this.get_at(key_kind, key_value, _start_from_time, out._this)
        if not res.has_value():
            raise_std_error(res.error())
        return out

    def get_at_slant_height(self, double look_angle_rad, double value):
        """Get CythonizedBaseTrajData where value == slant_height === position.y*cos(a) - position.x*sin(a)."""
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBC_Result[monostate] res = self._this.get_at_slant_height(look_angle_rad, value, out._this)
        if not res.has_value():
            raise_std_error(res.error())
        return out


# @final is safe with abi3: no other Cython module subclasses this type.
# If you need to subclass it from another .pyx, remove @final — see engines.pyx for context.
@final
cdef class CythonizedBaseTrajData:
    __slots__ = ('time', 'position', 'velocity', 'mach')  # for pure python mirror consistency

    def __repr__(self):
        cls_name = self.__class__.__name__

        field_names = self.__slots__
        field_values = self.__iter__()

        content = ", ".join(
            f"{name}={repr(value)}"
            for name, value in zip(field_names, field_values)
        )
        return f"{cls_name}({content})"

    def __str__(self):
        content = ", ".join(repr(value) for value in self)
        return f"({content})"

    def __len__(self):
        return len(self.__slots__)

    def __iter__(self):
        yield self.time
        yield self.position
        yield self.velocity
        yield self.mach

    def __getitem__(self, index):
        """
        Implements access to fields by index: self[0] -> time, self[1] -> position, etc.
        Supports indexes and slices.
        """
        if index == 0:
            return self.time
        elif index == 1:
            return self.position
        elif index == 2:
            return self.velocity
        elif index == 3:
            return self.mach

        # Negative
        elif index == -4:
            return self.time
        elif index == -3:
            return self.position
        elif index == -2:
            return self.velocity
        elif index == -1:
            return self.mach

        # Slices
        elif isinstance(index, slice):
            return (self.time, self.position, self.velocity, self.mach)[index]

        raise IndexError("TrajData index out of range")

    def __eq__(self, other):
        """Implements self-comparison (self == other)."""
        if isinstance(other, CythonizedBaseTrajData):
            return (self.time == other.time and
                    self.position == other.position and
                    self.velocity == other.velocity and
                    self.mach == other.mach)

        elif len(self) == len(other):
            return all(a == b for a, b in zip(self, other))

        return NotImplemented

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
                    CythonizedBaseTrajData p0, CythonizedBaseTrajData p1, CythonizedBaseTrajData p2):
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation
        of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach',
                or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (CythonizedBaseTrajData):
                Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        cdef BCLIBC_BaseTrajData_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef CythonizedBaseTrajData out = CythonizedBaseTrajData()
        cdef BCLIBC_Result[monostate] res = BCLIBC_BaseTrajData.interpolate(
            key_kind, key_value,
            p0._this, p1._this, p2._this,
            out._this
        )
        if not res.has_value():
            raise ZeroDivisionError(res.error().what().decode("utf-8"))
        return out


cdef object TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data):
    cdef int f = <int>cpp_data.flag
    flag = _flags.get(f)
    if flag is None:
        flag = _flags[f] = TrajFlag(f)
    return _tuple_new(_TD, (
        cpp_data.time, _feet(cpp_data.distance_ft), _fps(cpp_data.velocity_fps), cpp_data.mach,
        _feet(cpp_data.height_ft), _feet(cpp_data.slant_height_ft), _rad(cpp_data.drop_angle_rad),
        _feet(cpp_data.windage_ft), _rad(cpp_data.windage_angle_rad), _feet(cpp_data.slant_distance_ft),
        _rad(cpp_data.angle_rad), cpp_data.density_ratio, cpp_data.drag, _ft_lb(cpp_data.energy_ft_lb),
        _lb(cpp_data.ogw_lb), flag,
    ))


cdef list TrajectoryData_list_from_cpp(const vector[BCLIBC_TrajectoryData] &records):
    cdef list py_list = []
    cdef size_t i
    cdef size_t n = records.size()

    for i in range(n):
        py_list.append(TrajectoryData_from_cpp(records[i]))

    return py_list
