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
from py_ballisticcalc_exts.bclib cimport (
    ErrorCode,
    BaseTrajData_t,
    InterpKey,
    BaseTrajData_t_interpolate,
    initLogLevel,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bind cimport _attribute_to_key, _v3d_to_vector


initLogLevel()


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, BaseTrajData_t data):
        self._c_view = data

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
        cdef InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef BaseTrajData_t out
        cdef ErrorCode err = BaseTrajData_t_interpolate(
            key_kind, key_value,
            &p0._c_view, &p1._c_view, &p2._c_view,
            &out
        )

        if err == ErrorCode.NO_ERROR:
            return BaseTrajDataT(out)

        if err == ErrorCode.VALUE_ERROR:
            raise ValueError("invalid BaseTrajData_t_interpolate input")
        if err == ErrorCode.KEY_ERROR:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        if err == ErrorCode.ZERO_DIVISION_ERROR:
            raise ZeroDivisionError("Duplicate x for interpolation")
        raise RuntimeError("unknown error in BaseTrajData_t_interpolate")
