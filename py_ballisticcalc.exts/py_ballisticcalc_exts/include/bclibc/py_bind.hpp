#ifndef BCLIBC_PY_BIND_HPP
#define BCLIBC_PY_BIND_HPP

// Cython only bindings
#ifdef __CYTHON__

#include <Python.h>
#include "base_types.hpp" // BCLIBC_MachList typedef must be here

namespace bclibc
{

    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject *config);
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist);
    BCLIBC_Atmosphere BCLIBC_Atmosphere_fromPyObject(PyObject *atmo);
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points);
    BCLIBC_Wind BCLIBC_Wind_fromPyObject(PyObject *w);

};

#endif // __CYTHON__

#endif // BCLIBC_PY_BIND_HPP
