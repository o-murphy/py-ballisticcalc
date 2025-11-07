# cython: freethreading_compatible=True
"""
Lightweight Cython data types for trajectory rows and interpolation helpers.

This module mirrors a subset of the Python API in py_ballisticcalc.trajectory_data:
 - BaseTrajDataT: minimal row with time, position (BCLIBC_V3dT), velocity (BCLIBC_V3dT), mach.

Primary producer/consumer is the Cython engines which operate on a dense C buffer
and convert to these types as needed for interpolation or presentation.
"""
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ErrorType,
    BCLIBC_BaseTrajData,
    BCLIBC_BaseTrajSeq_InterpKey,
    BCLIBC_BaseTrajData_interpolate,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bind cimport _attribute_to_key, v3d_to_vector


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, BCLIBC_BaseTrajData data):
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
        return v3d_to_vector(&self._c_view.position)

    @property
    def velocity(self):
        return v3d_to_vector(&self._c_view.velocity)

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
        cdef BCLIBC_BaseTrajSeq_InterpKey key_kind = _attribute_to_key(key_attribute)
        cdef BCLIBC_BaseTrajData out
        cdef BCLIBC_ErrorType err = BCLIBC_BaseTrajData_interpolate(
            key_kind, key_value,
            &p0._c_view, &p1._c_view, &p2._c_view,
            &out
        )

        if err == BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
            return BaseTrajDataT(out)

        if err == BCLIBC_ErrorType.BCLIBC_E_VALUE_ERROR:
            raise ValueError("invalid BCLIBC_BaseTrajData_interpolate input")
        if err == BCLIBC_ErrorType.BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        if err == BCLIBC_ErrorType.BCLIBC_E_ZERO_DIVISION_ERROR:
            raise ZeroDivisionError("Duplicate x for interpolation")
        raise RuntimeError("unknown error in BCLIBC_BaseTrajData_interpolate")
