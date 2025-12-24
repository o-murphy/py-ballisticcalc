#ifndef BCLIBC_PY_BIND_HPP
#define BCLIBC_PY_BIND_HPP

// Cython only bindings
#ifdef __CYTHON__

#include <Python.h>
#include "bclibc/base_types.hpp" // BCLIBC_MachList typedef must be here

namespace bclibc
{

    /**
     * @brief Converts a Python configuration object to a native BCLIBC_Config.
     * @param config Pointer to a Python object representing configuration.
     * @return BCLIBC_Config populated from the Python object.
     */
    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject *config);

    /**
     * @brief Converts a Python list of Mach numbers to a native BCLIBC_MachList.
     * @param pylist Pointer to a Python list of floats (Mach numbers).
     * @return BCLIBC_MachList populated from the Python list.
     */
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist);

    /**
     * @brief Converts a Python object representing atmospheric conditions to BCLIBC_Atmosphere.
     * @param atmo Pointer to a Python object representing atmosphere.
     * @return BCLIBC_Atmosphere populated from the Python object.
     */
    BCLIBC_Atmosphere BCLIBC_Atmosphere_fromPyObject(PyObject *atmo);

    /**
     * @brief Converts a Python list of data points to a native BCLIBC_Curve.
     * @param data_points Pointer to a Python list of tuples or floats representing curve points.
     * @return BCLIBC_Curve populated from the Python list.
     */
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points);

}; // namespace bclibc

#endif // __CYTHON__

#endif // BCLIBC_PY_BIND_HPP
