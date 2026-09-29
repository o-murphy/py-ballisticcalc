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

    /**
     * @brief Converts a Python Shot-like object's already-filled BCLIBC_Shot to a BCLIBC_ShotProps.
     *
     * bclibc::BCLIBC_Shot::to_shot_props() returns a Result instead of throwing; this wraps it,
     * setting a Python exception (RuntimeError) and returning a default-constructed BCLIBC_ShotProps
     * on failure, exactly like the other BCLIBC_*_fromPy* helpers in this header.
     * @param shot The BCLIBC_Shot to convert.
     * @return BCLIBC_ShotProps on success, or a default-constructed one with a Python exception set.
     */
    BCLIBC_ShotProps BCLIBC_ShotProps_from_BCLIBC_Shot(const BCLIBC_Shot &shot);

    /**
     * @brief Wraps BCLIBC_ShotProps::update_stability_coefficient(), which returns a Result
     * instead of throwing. Sets a Python ZeroDivisionError and returns false on failure.
     */
    bool BCLIBC_ShotProps_update_stability_coefficient(BCLIBC_ShotProps &props);

    /**
     * @brief Wraps BCLIBC_ShotProps::drag_by_mach(), which returns a Result instead of
     * throwing. Sets a Python ValueError and returns false on failure; the drag value is
     * written to `out` only on success.
     */
    bool BCLIBC_ShotProps_drag_by_mach(const BCLIBC_ShotProps &props, double mach, double &out);

}; // namespace bclibc

#endif // __CYTHON__

#endif // BCLIBC_PY_BIND_HPP
