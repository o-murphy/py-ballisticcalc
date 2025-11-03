#ifndef BCLIBC_PY_BIND_H
#define BCLIBC_PY_BIND_H

#include <Python.h>
#include "bclibc_bclib.h" // BCLIBC_MachList typedef must be here

#ifdef __cplusplus
extern "C"
{
#endif

    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject *config);
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist);
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points);
    BCLIBC_Wind BCLIBC_Wind_fromPyObject(PyObject *w);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_PY_BIND_H
