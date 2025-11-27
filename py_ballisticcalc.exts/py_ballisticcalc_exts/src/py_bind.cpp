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
                PyErr_SetString(PyExc_IndexError, "MachList: List index out of range during iteration.");
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
        // Check for PyList_Size error or insufficient data
        if (n < 2)
        {
            if (n < 0)
            {
                // Error in Python List access
                return BCLIBC_Curve();
            }
            // insufficient data; return empty curve
            PyErr_SetString(PyExc_ValueError, "BCLIBC_Curve requires at least 2 data points.");
            return BCLIBC_Curve();
        }

        // --- Phase 1: Extract x (Mach) and y (CD) into vectors (RAII) ---
        // Instead of malloc(x) and malloc(y), we use std::vector.
        std::vector<double> x((size_t)n);
        std::vector<double> y((size_t)n);

        // If memory allocation fails here, std::vector will throw std::bad_alloc,
        // which Cython's 'except +' will catch.

        for (Py_ssize_t i = 0; i < n; ++i)
        {
            PyObject *item = PyList_GetItem(data_points, i); // borrowed
            // Note: PyList_GetItem should not return nullptr here unless list size changed,
            // but we keep the check for robustness.
            if (item == nullptr)
            {
                PyErr_SetString(PyExc_IndexError, "Curve generation: List item access failed.");
                return BCLIBC_Curve();
            }

            // Get x (Mach) and y (CD) attributes
            PyObject *xobj = PyObject_GetAttrString(item, "Mach"); // new ref
            PyObject *yobj = PyObject_GetAttrString(item, "CD");   // new ref

            if (xobj == nullptr || yobj == nullptr)
            {
                // Attribute access failed (PyErr_Occurred is true)
                Py_XDECREF(xobj);
                Py_XDECREF(yobj);
                return BCLIBC_Curve();
            }

            // Convert and assign
            x[i] = PyFloat_AsDouble(xobj);
            y[i] = PyFloat_AsDouble(yobj);

            Py_DECREF(xobj);
            Py_DECREF(yobj);

            if (PyErr_Occurred())
            {
                // Conversion failed (e.g., attribute was not a number)
                return BCLIBC_Curve();
            }
        }

        // --- Phase 2: Calculate PCHIP Slopes and Coefficients ---

        Py_ssize_t nm1 = n - 1;

        // Temporary vectors for PCHIP calculation (RAII: no more free calls!)
        std::vector<double> h((size_t)nm1); // Steps h[i] = x[i+1] - x[i]
        std::vector<double> d((size_t)nm1); // Slopes d[i] = (y[i+1] - y[i]) / h[i]
        std::vector<double> m((size_t)n);   // Final calculated slopes m[i]

        // Final result vector (n-1 segments)
        BCLIBC_Curve curve_points((size_t)nm1);

        for (Py_ssize_t i = 0; i < nm1; ++i)
        {
            h[i] = x[i + 1] - x[i];
            d[i] = (y[i + 1] - y[i]) / h[i];
        }

        if (n == 2)
        {
            m[0] = d[0];
            m[1] = d[0];
        }
        else
        {
            // Interior slopes (Fritsch–Carlson algorithm)
            for (Py_ssize_t i = 1; i < n - 1; ++i)
            {
                if (d[i - 1] == 0.0 || d[i] == 0.0 || d[i - 1] * d[i] < 0.0)
                {
                    m[i] = 0.0;
                }
                else
                {
                    double w1 = 2.0 * h[i] + h[i - 1];
                    double w2 = h[i] + 2.0 * h[i - 1];
                    m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
                }
            }

            // Endpoint m[0]
            double m0 = ((2.0 * h[0] + h[1]) * d[0] - h[0] * d[1]) / (h[0] + h[1]);
            if (m0 * d[0] <= 0.0)
                m0 = 0.0;
            else if ((d[0] * d[1] < 0.0) && (std::fabs(m0) > 3.0 * std::fabs(d[0])))
                m0 = 3.0 * d[0];
            m[0] = m0;

            // Endpoint m[n-1]
            double mn = ((2.0 * h[n - 2] + h[n - 3]) * d[n - 2] - h[n - 2] * d[n - 3]) / (h[n - 2] + h[n - 3]);
            if (mn * d[n - 2] <= 0.0)
                mn = 0.0;
            else if ((d[n - 2] * d[n - 3] < 0.0) && (std::fabs(mn) > 3.0 * std::fabs(d[n - 2])))
                mn = 3.0 * d[n - 2];
            m[n - 1] = mn;
        }

        // Build per-segment cubic coefficients in dx=(x-x_i):
        for (Py_ssize_t i = 0; i < nm1; ++i)
        {
            double H = h[i];
            double yi = y[i];
            double mi = m[i];
            double mip1 = m[i + 1];

            // A and B helpers
            double A = (y[i + 1] - yi - mi * H) / (H * H);
            double B = (mip1 - mi) / H;

            double a = (B - 2.0 * A) / H;
            double b = 3.0 * A - B;

            // Assign directly to the final curve vector element
            curve_points[i].a = a;
            curve_points[i].b = b;
            curve_points[i].c = mi;
            curve_points[i].d = yi;
        }

        // When we return curve_points, all temporary vectors (x, y, h, d, m)
        // are automatically destroyed and memory freed.
        return curve_points;
    }

    /**
     * @brief Converts a Python object representing wind to a native BCLIBC_Wind.
     * @param w Pointer to a Python object representing wind conditions.
     * @return BCLIBC_Wind populated from the Python object.
     */
    BCLIBC_Wind BCLIBC_Wind_fromPyObject(PyObject *w)
    {
        // Initialize the C structure to zero values in case of error.
        BCLIBC_Wind wind_c = {0.0, 0.0, 0.0, 0.0};

        // Temporary variables for Python objects during attribute lookup.
        // Initialized to NULL for safety, although the current flow relies on Py_DECREF.
        PyObject *tmp_vel = nullptr;
        PyObject *tmp_dir = nullptr;
        PyObject *tmp_dist = nullptr;
        PyObject *tmp_max = nullptr;

        // Temporary variables for the final attribute values (e.g., _fps, _rad, _feet)
        PyObject *fps_obj = nullptr;
        PyObject *rad_obj = nullptr;
        PyObject *feet_obj = nullptr;

        // --- 1. Get w.velocity._fps ---
        // Check if an error occurred in a previous step before proceeding.
        if (PyErr_Occurred() == nullptr)
        {
            // Get the 'velocity' attribute (returns a new reference)
            tmp_vel = PyObject_GetAttrString(w, "velocity");
            if (tmp_vel != nullptr)
            {
                // Get the '_fps' attribute (returns a new reference)
                fps_obj = PyObject_GetAttrString(tmp_vel, "_fps");
                Py_DECREF(tmp_vel); // Release the reference to the intermediate 'velocity' object
                if (fps_obj != nullptr)
                {
                    // Convert to double. PyFloat_AsDouble checks for errors internally.
                    wind_c.velocity = PyFloat_AsDouble(fps_obj);
                    Py_DECREF(fps_obj); // Release the reference to the '_fps' value object
                }
            }
            // If PyObject_GetAttrString or PyFloat_AsDouble failed, PyErr_Occurred() is set.
        }

        // --- 2. Get w.direction_from._rad ---
        if (PyErr_Occurred() == nullptr)
        {
            tmp_dir = PyObject_GetAttrString(w, "direction_from");
            if (tmp_dir != nullptr)
            {
                rad_obj = PyObject_GetAttrString(tmp_dir, "_rad");
                Py_DECREF(tmp_dir);
                if (rad_obj != nullptr)
                {
                    wind_c.direction_from = PyFloat_AsDouble(rad_obj);
                    Py_DECREF(rad_obj);
                }
            }
        }

        // --- 3. Get w.until_distance._feet ---
        if (PyErr_Occurred() == nullptr)
        {
            tmp_dist = PyObject_GetAttrString(w, "until_distance");
            if (tmp_dist != nullptr)
            {
                feet_obj = PyObject_GetAttrString(tmp_dist, "_feet");
                Py_DECREF(tmp_dist);
                if (feet_obj != nullptr)
                {
                    wind_c.until_distance = PyFloat_AsDouble(feet_obj);
                    Py_DECREF(feet_obj);
                }
            }
        }

        // --- 4. Get w.MAX_DISTANCE_FEET ---
        if (PyErr_Occurred() == nullptr)
        {
            // Get the direct attribute (returns a new reference)
            tmp_max = PyObject_GetAttrString(w, "MAX_DISTANCE_FEET");
            if (tmp_max != nullptr)
            {
                wind_c.MAX_DISTANCE_FEET = PyFloat_AsDouble(tmp_max);
                Py_DECREF(tmp_max);
            }
        }

        // Check if a Python exception occurred during any attribute lookup or conversion.
        if (PyErr_Occurred())
        {
            // If an error is set, return the zeroed structure.
            // The calling Cython code is responsible for checking PyErr_Occurred() and raising the exception.
            BCLIBC_Wind err_wind = {0.0, 0.0, 0.0, 0.0};
            return err_wind;
        }

        return wind_c;
    };
}; // namespace bclibc

#endif // __CYTHON__
