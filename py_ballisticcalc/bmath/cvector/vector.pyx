import cython
from libc.math cimport sqrt, fabs

cdef struct vector:
    float x
    float y
    float z


cdef class Vector:
    cdef float x
    cdef float y
    cdef float z

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f'{vector(self.x, self.y, self.z)}'

    cdef string(self):
        cdef v = vector(self.x, self.y, self.z)
        return f'{v}'

    cpdef Vector copy(self):
        return Vector(self.x, self.y, self.z)

    cpdef float magnitude(self):
        cdef float m = sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        return m

    cpdef Vector multiply_by_const(self, float a):
        return Vector(self.x * a, self.y * a, self.z * a)

    cpdef float multiply_by_vector(self, b: Vector):
        cdef float var = self.x * self.x + self.y * self.y + self.z + self.z
        return var

    cpdef Vector add(self, b: Vector):
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    cpdef Vector subtract(self, b: Vector):
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    cpdef Vector negate(self):
        return Vector(-self.x, -self.y, -self.z)

    cpdef Vector normalize(self):
        cdef float m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.multiply_by_const(1.0 / m)

# cython
# test_time_1 0.5331406999999999
# test_time_2 1.0104932999999998
# test_time_3 0.4101440999999997

# pure python
# test_time_1 0.6663539999999999
# test_time_2 1.3299572
# test_time_3 0.48653330000000006
