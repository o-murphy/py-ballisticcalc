from libc.math cimport sqrt, fabs
from cython cimport final
# from py_ballisticcalc_exts._data_repr cimport _Comparable

try:
    import typing
    import dataclasses
except ImportError:
    pass  # The modules don't actually have to exists for Cython to use them as annotations

__all__ = ('Vector',)

@final
@dataclasses.dataclass
cdef class Vector:

    def __cinit__(Vector self, double x, double y, double z):
        self._x = x
        self._y = y
        self._z = z

    @property
    def x(self: Vector) -> float:
        return self._x

    @x.setter
    def x(self, double v) -> None:
        self._x = v

    @property
    def y(self: Vector) -> float:
        return self._y

    @y.setter
    def y(self, double v) -> None:
        self._y = v

    @property
    def z(self: Vector) -> float:
        return self._z

    @z.setter
    def z(self, double v) -> None:
        self._z = v

    cdef double _magnitude(Vector self):
        return sqrt(self._x * self._x + self._y * self._y + self._z * self._z)

    def magnitude(Vector self):
        return self._magnitude()

    cdef Vector _mul_by_const(Vector self, double a):
        return Vector(self._x * a, self._y * a, self._z * a)

    def mul_by_const(Vector self, double a):
        return self._mul_by_const(a)

    cdef double _mul_by_vector(Vector self, Vector b):
        return self._x * b._x + self._y * b._y + self._z * b._z

    def mul_by_vector(Vector self, Vector b):
        return self._mul_by_vector(b)

    cdef Vector _add(Vector self, Vector b):
        return Vector(self._x + b._x, self._y + b._y, self._z + b._z)

    def add(Vector self, Vector b):
        return self._add(b)

    cdef Vector _subtract(Vector self, Vector b):
        return Vector(self._x - b._x, self._y - b._y, self._z - b._z)

    def subtract(Vector self, Vector b):
        return self._subtract(b)

    cdef Vector _negate(Vector self):
        return Vector(-self._x, -self._y, -self._z)

    def negate(Vector self):
        return self._negate()

    cdef Vector _normalize(Vector self):
        cdef double m = self._magnitude()
        if fabs(m) < 1e-10:
            return Vector(self._x, self._y, self._z)
        return self._mul_by_const(1.0 / m)

    def normalize(Vector self):
        return self._normalize()

    def __add__(Vector self, Vector other):
        return self._add(other)

    def __radd__(Vector self, Vector other):
        return self._add(other)

    def __iadd__(Vector self, Vector other):
        return self._add(other)

    def __sub__(Vector self, Vector other):
        return self._subtract(other)

    def __rsub__(Vector self, Vector other):
        return self._subtract(other)

    def __isub__(Vector self, Vector other):
        return self._subtract(other)

    def __mul__(Vector self, object other):
        if isinstance(other, (int, float)):
            return self._mul_by_const(<double>other)
        if isinstance(other, Vector):
            return self._mul_by_vector(<Vector>other)
        raise TypeError(other)

    def __rmul__(Vector self, object other):
        return self.__mul__(other)

    def __imul__(Vector self, object other):
        return self.__mul__(other)

    def __neg__(Vector self):
        return self._negate()

    def __str__(Vector self):
        return f"Vector(x={self._x}, y={self._y}, z={self._z})"

    cdef CVector c_vector(Vector self):
        return CVector(self._x, self._y, self._z)


cdef double mag(CVector * v):
    return sqrt(v.x * v.x + v.y * v.y + v.z * v.z)

cdef CVector mul_c(CVector * v, double a):
    return CVector(v.x * a, v.y * a, v.z * a)

cdef double mul_v(CVector * v, CVector * b):
    return v.x * b.x + v.y * b.y + v.z * b.z

cdef CVector add(CVector * v, CVector * b):
    return CVector(v.x + b.x, v.y + b.y, v.z + b.z)

cdef CVector sub(CVector * v, CVector * b):
    return CVector(v.x - b.x, v.y - b.y, v.z - b.z)

cdef CVector neg(CVector * v):
    return CVector(-v.x, -v.y, -v.z)

cdef CVector norm(CVector * v):
    cdef double m = mag(v)
    if fabs(m) < 1e-10:
        return CVector(v.x, v.y, v.z)
    return mul_c(v, 1.0 / m)