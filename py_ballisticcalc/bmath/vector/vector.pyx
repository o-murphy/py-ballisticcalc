from libc.math cimport sqrt, fabs
from typing import Any


cdef struct vector:
    double x
    double y
    double z


cdef class Vector:
    cdef double _x
    cdef double _y
    cdef double _z

    def __init__(self, x: double, y: double, z: double):
        self._x = x
        self._y = y
        self._z = z

    def __str__(self):
        return f'{vector(self._x, self._y, self._z)}'

    cpdef double x(self):
        return self._x

    cpdef double y(self):
        return self._y

    cpdef double z(self):
        return self._z

    cdef string(self):
        cdef v = vector(self._x, self._y, self._z)
        return f'{v}'

    cpdef Vector copy(self):
        return Vector(self._x, self._y, self._z)

    cpdef double magnitude(self):
        cdef double m = sqrt(self._x * self._x + self._y * self._y + self._z * self._z)
        return m

    cpdef Vector multiply_by_const(self, float a):
        return Vector(self._x * a, self._y * a, self._z * a)

    cpdef double multiply_by_vector(self, b: Vector):
        cdef double var = self._x * b._x + self._y * b._y + self._z * b._z
        return var

    cpdef Vector add(self, b: Vector):
        return Vector(self._x + b._x, self._y + b._y, self._z + b._z)

    cpdef Vector subtract(self, b: Vector):
        return Vector(self._x - b._x, self._y - b._y, self._z - b._z)

    cpdef Vector negate(self):
        return Vector(-self._x, -self._y, -self._z)

    cpdef Vector normalize(self):
        cdef double m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self._x, self._y, self._z)
        return self.multiply_by_const(1.0 / m)

    def __add__(self, other: Vector):
        return self.add(other)

    def __radd__(self, other: Vector):
        return self.__add__(other)

    def __iadd__(self, other: Vector):
        return self.__add__(other)

    def __sub__(self, other: Vector):
        return self.subtract(other)

    def __rsub__(self, other: Vector):
        return other.subtract(self)

    def __isub__(self, other: Vector):
        return self.subtract(other)

    def __mul__(self, other: [Vector, float, int]):
        if isinstance(other, int) or isinstance(other, float):
            return self.multiply_by_const(other)
        elif isinstance(other, Vector):
            return self.multiply_by_vector(other)
        else:
            raise TypeError(other)

    def __rmul__(self, other: [Vector, float, int]):
        return self.__mul__(other)

    def __imul__(self, other: [Vector, float, int]):
        return self.__mul__(other)

    def __neg__(self):
        return self.negate()

    def __iter__(self):
        yield self.x()
        yield self.y()
        yield self.z()
