# from py_ballisticcalc_exts._data_repr cimport _Comparable


cdef class Vector:
    cdef double _x
    cdef double _y
    cdef double _z

    cdef double _magnitude(Vector self)
    cdef Vector _mul_by_const(Vector self, double a)
    cdef double _mul_by_vector(Vector self, Vector b)
    cdef Vector _add(Vector self, Vector b)
    cdef Vector _subtract(Vector self, Vector b)
    cdef Vector _negate(Vector self)
    cdef Vector _normalize(Vector self)
