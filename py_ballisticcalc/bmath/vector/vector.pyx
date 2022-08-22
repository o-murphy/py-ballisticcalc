from libc.math cimport sqrt, fabs

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

# cython
# test_time_1 0.5331406999999999
# test_time_2 1.0104932999999998
# test_time_3 0.4101440999999997

# pure python
# test_time_1 0.6663539999999999
# test_time_2 1.3299572
# test_time_3 0.48653330000000006
