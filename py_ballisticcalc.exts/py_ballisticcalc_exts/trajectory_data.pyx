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
from py_ballisticcalc_exts.interp cimport interpolate_3_pt
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BaseTrajData_t,
    BaseTrajData_t_create,
    BaseTrajData_t_destroy,
    InterpKey,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bind cimport _attribute_to_key, _v3d_to_vector

from py_ballisticcalc.vector import Vector


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, BaseTrajData_t data):
        self._c_view = data


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
        cdef InterpKey key_kind = _attribute_to_key(key_attribute)

        cdef:
            double x0, x1, x2
            double time, mach
            V3dT position, velocity
            BaseTrajDataT _p0
            BaseTrajDataT _p1
            BaseTrajDataT _p2
            V3dT vp0, vp1, vp2, vv0, vv1, vv2

        _p0 = <BaseTrajDataT> p0
        _p1 = <BaseTrajDataT> p1
        _p2 = <BaseTrajDataT> p2

        vp0 = _p0.c_position()
        vp1 = _p1.c_position()
        vp2 = _p2.c_position()
        vv0 = _p0.c_velocity()
        vv1 = _p1.c_velocity()
        vv2 = _p2.c_velocity()

        # Determine independent variable values from key_attribute
        if key_kind == InterpKey.KEY_TIME:
            x0 = _p0.time
            x1 = _p1.time
            x2 = _p2.time
        elif key_kind == InterpKey.KEY_MACH:
            x0 = _p0.mach
            x1 = _p1.mach
            x2 = _p2.mach
        elif key_kind == InterpKey.KEY_POS_X:
            x0 = vp0.x
            x1 = vp1.x
            x2 = vp2.x
        elif key_kind == InterpKey.KEY_POS_Y:
            x0 = vp0.y
            x1 = vp1.y
            x2 = vp2.y
        elif key_kind == InterpKey.KEY_POS_Z:
            x0 = vp0.z
            x1 = vp1.z
            x2 = vp2.z
        elif key_kind == InterpKey.KEY_VEL_X:
            x0 = vv0.x
            x1 = vv1.x
            x2 = vv2.x
        elif key_kind == InterpKey.KEY_VEL_Y:
            x0 = vv0.y
            x1 = vv1.y
            x2 = vv2.y
        elif key_kind == InterpKey.KEY_VEL_Z:
            x0 = vv0.z
            x1 = vv1.z
            x2 = vv2.z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        # Guard against degenerate segments
        if x0 == x1 or x0 == x2 or x1 == x2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        # Scalar interpolation using PCHIP

        # Interpolate all scalar fields
        time = key_value if key_kind == InterpKey.KEY_TIME else interpolate_3_pt(
            key_value, x0, x1, x2, _p0.time, _p1.time, _p2.time
        )
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
        mach = key_value if key_kind == InterpKey.KEY_MACH else interpolate_3_pt(
            key_value, x0, x1, x2, _p0.mach, _p1.mach, _p2.mach
        )

        # Construct the resulting BaseTrajDataT
        return BaseTrajDataT(BaseTrajData_t(time, position, velocity, mach))
