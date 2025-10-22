# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport BaseTrajData_t

cdef class BaseTrajDataT:
    cdef:
        BaseTrajData_t _c_view
