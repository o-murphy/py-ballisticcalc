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



cdef double mag(const CVector * v)
cdef CVector mul_c(const CVector * v, double a)
cdef double mul_v(const CVector * v, const CVector * b)
cdef CVector add(const CVector * v, const CVector * b)
cdef CVector sub(const CVector * v, const CVector * b)
cdef CVector neg(const CVector * v)
cdef CVector norm(const CVector * v)