# from py_ballisticcalc_exts._data_repr cimport _Comparable
cdef struct CVector:
    double x, y, z


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

    cdef CVector c_vector(Vector self)



cdef double mag(CVector * v)
cdef CVector mul_c(CVector * v, double a)
cdef double mul_v(CVector * v, CVector * b)
cdef CVector add(CVector * v, CVector * b)
cdef CVector sub(CVector * v, CVector * b)
cdef CVector neg(CVector * v)
cdef CVector norm(CVector * v)