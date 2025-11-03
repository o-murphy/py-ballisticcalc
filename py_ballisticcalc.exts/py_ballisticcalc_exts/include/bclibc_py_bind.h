#ifndef BCLIBC_PY_BIND_H
#define BCLIBC_PY_BIND_H

#include <Python.h>
#include "bclibc_bclib.h" // MachList_t typedef must be here

#ifdef __cplusplus
extern "C"
{
#endif

    Config_t Config_t_fromPyObject(PyObject *config);
    MachList_t MachList_t_fromPylist(PyObject *pylist);
    Curve_t Curve_t_fromPylist(PyObject *data_points);
    Wind_t Wind_t_fromPyObject(PyObject *w);

#ifdef __cplusplus
}
#endif

#endif // BCLIBC_PY_BIND_H
