// Cython only bindings
#ifdef __CYTHON__

#include <cstdlib>
#include <cmath>
#include "bclibc/py_bind.hpp"

namespace bclibc
{
    /**
     * @brief Converts a Python configuration object to a native BCLIBC_Config.
     * @param config Pointer to a Python object representing configuration.
     * @return BCLIBC_Config populated from the Python object.
     */
    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject *config)
    {
        return BCLIBC_Config{
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cStepMultiplier")),
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cZeroFindingAccuracy")),
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cMinimumVelocity")),
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cMaximumDrop")),
            (int)PyLong_AsLong(PyObject_GetAttrString(config, "cMaxIterations")),
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cGravityConstant")),
            PyFloat_AsDouble(PyObject_GetAttrString(config, "cMinimumAltitude"))};
    };

    /**
     * @brief Converts a Python object representing atmospheric conditions to BCLIBC_Atmosphere.
     * @param atmo Pointer to a Python object representing atmosphere.
     * @return BCLIBC_Atmosphere populated from the Python object.
     */
    BCLIBC_Atmosphere BCLIBC_Atmosphere_fromPyObject(PyObject *atmo)
    {
        return BCLIBC_Atmosphere(
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "_t0")),
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "_a0")),
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "_p0")),
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "_mach")),
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "density_ratio")),
            PyFloat_AsDouble(PyObject_GetAttrString(atmo, "cLowestTempC")));
    };

    /**
     * @brief Converts a Python list of Mach numbers to a native BCLIBC_MachList.
     * @param pylist Pointer to a Python list of floats (Mach numbers).
     * @return BCLIBC_MachList populated from the Python list.
     */
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist)
    {
        BCLIBC_MachList mach_list;
        Py_ssize_t len = PyList_Size(pylist);

        // Check for PyList_Size error (returns -1 on failure)
        if (len < 0)
        {
            return mach_list; // Returns empty vector
        }

        // Pre-allocate memory in the vector for efficiency
        mach_list.reserve((size_t)len);

        for (Py_ssize_t i = 0; i < len; i++)
        {
            // PyList_GetItem returns a borrowed reference
            PyObject *item = PyList_GetItem(pylist, i);
            if (item == nullptr)
            {
                // Should not happen if size is correct, but handles unexpected issues.
                PyErr_SetString(PyExc_IndexError, "MachList: list index out of range during iteration.");
                // Vector destructor is automatically called, freeing any allocated memory.
                return BCLIBC_MachList();
            }

            // Get the .Mach attribute
            // PyObject_GetAttrString returns a new reference (must be DECREF'd)
            PyObject *mach_obj = PyObject_GetAttrString(item, "Mach");
            if (mach_obj == nullptr)
            {
                // Error (attribute not found), Python exception already set.
                return BCLIBC_MachList();
            }

            // Convert to double
            double mach = PyFloat_AsDouble(mach_obj);
            Py_DECREF(mach_obj); // Release the reference obtained from GetAttrString

            if (PyErr_Occurred())
            {
                // Conversion error (e.g., non-numeric value), Python exception already set.
                return BCLIBC_MachList();
            }

            // Add the element to the vector.
            // No manual memory management (malloc/free) is needed.
            mach_list.push_back(mach);
        }

        return mach_list;
    }

    /**
     * @brief Creates a BCLIBC_Curve (std::vector<BCLIBC_CurvePoint>) from a Python list
     * of objects, extracting Mach (x) and CD (y) and calculating PCHIP coefficients.
     * * Uses std::vector for all temporary arrays (x, y, h, d, m), eliminating all manual
     * memory management (malloc/free) and ensuring exception safety.
     *
     * @param data_points Python list object.
     * @return BCLIBC_Curve containing PCHIP segment coefficients. Returns an empty vector
     * and ensures Python exception is set on error.
     */
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points)
    {
        Py_ssize_t n = PyList_Size(data_points);
        if (n < 2)
        {
            if (n < 0)
                return BCLIBC_Curve();
            PyErr_SetString(PyExc_ValueError, "BCLIBC_Curve requires at least 2 data points.");
            return BCLIBC_Curve();
        }

        // --- Phase 1: Prepare data ---
        std::vector<double> x((size_t)n);
        std::vector<double> y((size_t)n);

        for (Py_ssize_t i = 0; i < n; ++i)
        {
            PyObject *item = PyList_GetItem(data_points, i);
            if (item == nullptr)
            {
                PyErr_SetString(PyExc_IndexError, "Curve generation: list item access failed.");
                return BCLIBC_Curve();
            }

            PyObject *xobj = PyObject_GetAttrString(item, "Mach");
            PyObject *yobj = PyObject_GetAttrString(item, "CD");

            if (xobj == nullptr || yobj == nullptr)
            {
                Py_XDECREF(xobj);
                Py_XDECREF(yobj);
                return BCLIBC_Curve();
            }

            x[i] = PyFloat_AsDouble(xobj);
            y[i] = PyFloat_AsDouble(yobj);

            Py_DECREF(xobj);
            Py_DECREF(yobj);

            if (PyErr_Occurred())
                return BCLIBC_Curve();
        }

        // --- Phase 2: Call universal core ---
        return build_pchip_curve_from_arrays(x, y);
    }
}; // namespace bclibc

#endif // __CYTHON__
