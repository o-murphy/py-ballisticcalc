# cython: freethreading_compatible=True
"""
Lightweight Cython data types for trajectory rows and interpolation helpers.

This module mirrors a subset of the Python API in py_ballisticcalc.trajectory_data:
 - BaseTrajDataT: minimal row with time, position (V3dT), velocity (V3dT), mach.

Primary producer/consumer is the Cython engines which operate on a dense C buffer
and convert to these types as needed for interpolation or presentation.
"""
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc.vector import Vector
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.interp cimport interpolate_3_pt


cdef object _v3d_to_vector(const V3dT *v):
    """Convert C V3dT -> Python Vector"""
    return Vector(v.x, v.y, v.z)


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, double time, V3dT position, V3dT velocity, double mach):
        self._c_view = BaseTrajData_t_create(time, position, velocity, mach)
        if self._c_view is NULL:
            raise MemoryError("Failed to create BaseTrajSeq_t")

    def __dealloc__(self):
        if self._c_view is not NULL:
            BaseTrajData_t_destroy(self._c_view)
            self._c_view = NULL

    # Hot-path C accessors (used by Cython code directly)
    cdef V3dT c_position(self):
        return self._c_view.position

    cdef V3dT c_velocity(self):
        return self._c_view.velocity

    @property
    def time(self):
        return self._c_view.time

    @property
    def mach(self):
        return self._c_view.mach

    # Python-facing properties return Vector, not dict
    @property
    def position(self):
        return _v3d_to_vector(&self._c_view.position)

    @property
    def velocity(self):
        return _v3d_to_vector(&self._c_view.velocity)

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                   object p0, object p1, object p2):
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach', or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (BaseTrajDataT): Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        cdef:
            double x0, x1, x2
            double time, mach
            V3dT position, velocity, vp0, vp1, vp2, vv0, vv1, vv2
            BaseTrajDataT _p0
            BaseTrajDataT _p1
            BaseTrajDataT _p2

        _p0 = <BaseTrajDataT> p0
        _p1 = <BaseTrajDataT> p1
        _p2 = <BaseTrajDataT> p2

        # Determine independent variable values from key_attribute
        if key_attribute == 'time':
            x0 = _p0.time
            x1 = _p1.time
            x2 = _p2.time
        elif key_attribute == 'mach':
            x0 = _p0.mach
            x1 = _p1.mach
            x2 = _p2.mach
        elif key_attribute == 'position.x':
            x0 = _p0.c_position().x
            x1 = _p1.c_position().x
            x2 = _p2.c_position().x
        elif key_attribute == 'position.y':
            x0 = _p0.c_position().y
            x1 = _p1.c_position().y
            x2 = _p2.c_position().y
        elif key_attribute == 'position.z':
            x0 = _p0.c_position().z
            x1 = _p1.c_position().z
            x2 = _p2.c_position().z
        elif key_attribute == 'velocity.x':
            x0 = _p0.c_velocity().x
            x1 = _p1.c_velocity().x
            x2 = _p2.c_velocity().x
        elif key_attribute == 'velocity.y':
            x0 = _p0.c_velocity().y
            x1 = _p1.c_velocity().y
            x2 = _p2.c_velocity().y
        elif key_attribute == 'velocity.z':
            x0 = _p0.c_velocity().z
            x1 = _p1.c_velocity().z
            x2 = _p2.c_velocity().z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        # Guard against degenerate segments
        if x0 == x1 or x0 == x2 or x1 == x2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        # Scalar interpolation using PCHIP

        vp0 = _p0.c_position()
        vp1 = _p1.c_position()
        vp2 = _p2.c_position()
        vv0 = _p0.c_velocity()
        vv1 = _p1.c_velocity()
        vv2 = _p2.c_velocity()

        # Interpolate all scalar fields
        time = key_value if key_attribute == 'time' else interpolate_3_pt(key_value, x0, x1, x2, _p0.time, _p1.time, _p2.time)
        position = V3dT(
            interpolate_3_pt(key_value, x0, x1, x2, vp0.x, vp1.x, vp2.x),
            interpolate_3_pt(key_value, x0, x1, x2, vp0.y, vp1.y, vp2.y),
            interpolate_3_pt(key_value, x0, x1, x2, vp0.z, vp1.z, vp2.z)
        )
        velocity = V3dT(
            interpolate_3_pt(key_value, x0, x1, x2, vv0.x, vv1.x, vv2.x),
            interpolate_3_pt(key_value, x0, x1, x2, vv0.y, vv1.y, vv2.y),
            interpolate_3_pt(key_value, x0, x1, x2, vv0.z, vv1.z, vv2.z)
        )
        mach = key_value if key_attribute == 'mach' else interpolate_3_pt(key_value, x0, x1, x2, _p0.mach, _p1.mach, _p2.mach)

        # Construct the resulting BaseTrajDataT
        return BaseTrajDataT(time, position, velocity, mach)
