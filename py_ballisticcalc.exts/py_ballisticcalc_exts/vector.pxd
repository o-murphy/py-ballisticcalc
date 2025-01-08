cdef class Vector:
    cdef double _x
    cdef double _y
    cdef double _z

    cdef double magnitude(Vector self)
    cdef Vector mul_by_const(Vector self, double a)
    cdef double mul_by_vector(Vector self, Vector b)
    cdef Vector add(Vector self, Vector b)
    cdef Vector subtract(Vector self, Vector b)
    cdef Vector negate(Vector self)
    cdef Vector normalize(Vector self)
