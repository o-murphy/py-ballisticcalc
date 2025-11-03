# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport BCLIBC_BaseTrajData

cdef class BaseTrajDataT:
    cdef:
        BCLIBC_BaseTrajData _c_view
