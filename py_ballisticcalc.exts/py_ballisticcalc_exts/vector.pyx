from libc.math cimport sqrt, fabs
from cython cimport final

__all__ = ('Vector',)

@final
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

    cdef double magnitude(Vector self):
        return sqrt(self._x * self._x + self._y * self._y + self._z * self._z)

    cdef Vector mul_by_const(Vector self, double a):
        return Vector(self._x * a, self._y * a, self._z * a)

    cdef double mul_by_vector(Vector self, Vector b):
        return self._x * b._x + self._y * b._y + self._z * b._z

    cdef Vector add(Vector self, Vector b):
        return Vector(self._x + b._x, self._y + b._y, self._z + b._z)

    cdef Vector subtract(Vector self, Vector b):
        return Vector(self._x - b._x, self._y - b._y, self._z - b._z)

    cdef Vector negate(Vector self):
        return Vector(-self._x, -self._y, -self._z)

    cdef Vector normalize(Vector self):
        cdef double m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self._x, self._y, self._z)
        return self.mul_by_const(1.0 / m)

    def __add__(Vector self, Vector other):
        return self.add(other)

    def __radd__(Vector self, Vector other):
        return self.add(other)

    def __iadd__(Vector self, Vector other):
        return self.add(other)

    def __sub__(Vector self, Vector other):
        return self.subtract(other)

    def __rsub__(Vector self, Vector other):
        return self.subtract(other)

    def __isub__(Vector self, Vector other):
        return self.subtract(other)

    def __mul__(Vector self, object other):
        if isinstance(other, (int, float)):
            return self.mul_by_const(<double>other)
        if isinstance(other, Vector):
            return self.mul_by_vector(<Vector>other)
        raise TypeError(other)

    def __rmul__(Vector self, object other):
        return self.__mul__(other)

    def __imul__(Vector self, object other):
        return self.__mul__(other)

    def __neg__(Vector self):
        return self.negate()

    def __str__(Vector self):
        return f"Vector(x={self._x}, y={self._y}, z={self._z})"
