#ifndef BIND_H
#define BIND_H

#include <Python.h>
#include <stdlib.h>
#include <math.h>
#include "bclib.h"
#include "bind.h"


Config_t Config_t_fromPyObject(PyObject* config) {
    Config_t c;

    PyObject* tmp;

    tmp = PyObject_GetAttrString(config, "cStepMultiplier");
    c.cStepMultiplier = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cZeroFindingAccuracy");
    c.cZeroFindingAccuracy = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cMinimumVelocity");
    c.cMinimumVelocity = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cMaximumDrop");
    c.cMaximumDrop = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cMaxIterations");
    c.cMaxIterations = (int)PyLong_AsLong(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cGravityConstant");
    c.cGravityConstant = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp = PyObject_GetAttrString(config, "cMinimumAltitude");
    c.cMinimumAltitude = PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    return c;
}


/**
 * Create MachList_t from a Python list of objects with `.Mach` attribute.
 * Returns MachList_t with allocated array or with array==NULL on error.
 * Caller responsible for freeing ml.array.
 */
MachList_t MachList_t_fromPylist(PyObject *pylist) {
    MachList_t ml = {NULL, 0};
    Py_ssize_t len = PyList_Size(pylist);
    if (len < 0) return ml;  // error

    ml.array = (double *)malloc(len * sizeof(double));
    if (ml.array == NULL) return ml;

    ml.length = (size_t)len;

    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject *item = PyList_GetItem(pylist, i);  // borrowed ref
        if (item == NULL) {
            free(ml.array);
            ml.array = NULL;
            ml.length = 0;
            return ml;
        }

        // Get .Mach attribute (assumes it exists and is float convertible)
        PyObject *mach_obj = PyObject_GetAttrString(item, "Mach");
        if (mach_obj == NULL) {
            free(ml.array);
            ml.array = NULL;
            ml.length = 0;
            return ml;
        }

        double mach = PyFloat_AsDouble(mach_obj);
        Py_DECREF(mach_obj);

        if (PyErr_Occurred()) {
            free(ml.array);
            ml.array = NULL;
            ml.length = 0;
            return ml;
        }

        ml.array[i] = mach;
    }

    return ml;
}

Curve_t Curve_t_fromPylist(PyObject *data_points) {
    Curve_t curve = {NULL, 0};
    Py_ssize_t n = PyList_Size(data_points);
    if (n < 2)  // need at least 2 points
        return curve;

    // Allocate arrays for knots and values
    double *x = (double *)malloc((size_t)n * sizeof(double));
    double *y = (double *)malloc((size_t)n * sizeof(double));
    if (x == NULL || y == NULL) {
        if (x) free(x);
        if (y) free(y);
        return curve;
    }

    // Extract Mach (x) and CD (y) from Python list
    for (Py_ssize_t i = 0; i < n; ++i) {
        PyObject *item = PyList_GetItem(data_points, i);  // borrowed
        if (item == NULL) { free(x); free(y); return curve; }
        PyObject *xobj = PyObject_GetAttrString(item, "Mach");
        PyObject *yobj = PyObject_GetAttrString(item, "CD");
        if (xobj == NULL || yobj == NULL) { Py_XDECREF(xobj); Py_XDECREF(yobj); free(x); free(y); return curve; }
        x[i] = PyFloat_AsDouble(xobj);
        y[i] = PyFloat_AsDouble(yobj);
        Py_DECREF(xobj);
        Py_DECREF(yobj);
        if (PyErr_Occurred()) { free(x); free(y); return curve; }
    }

    // Allocate segment coefficients (n-1 segments)
    CurvePoint_t *curve_points = (CurvePoint_t *) malloc((size_t)(n - 1) * sizeof(CurvePoint_t));
    if (!curve_points) { free(x); free(y); return curve; }

    // Prepare PCHIP slopes using Fritsch–Carlson algorithm
    Py_ssize_t nm1 = n - 1;
    double *h = (double *)malloc((size_t)nm1 * sizeof(double));
    double *d = (double *)malloc((size_t)nm1 * sizeof(double));
    double *m = (double *)malloc((size_t)n * sizeof(double));
    if (h == NULL || d == NULL || m == NULL) {
        if (h) free(h);
        if (d) free(d);
        if (m) free(m);
        free(curve_points);
        free(x);
        free(y);
        return curve;
    }

    for (Py_ssize_t i = 0; i < nm1; ++i) {
        h[i] = x[i+1] - x[i];
        d[i] = (y[i+1] - y[i]) / h[i];
    }

    if (n == 2) {
        m[0] = d[0];
        m[1] = d[0];
    } else {
        // Interior slopes
        for (Py_ssize_t i = 1; i < n - 1; ++i) {
            if (d[i-1] == 0.0 || d[i] == 0.0 || d[i-1] * d[i] < 0.0) {
                m[i] = 0.0;
            } else {
                double w1 = 2.0 * h[i] + h[i-1];
                double w2 = h[i] + 2.0 * h[i-1];
                m[i] = (w1 + w2) / (w1 / d[i-1] + w2 / d[i]);
            }
        }
        // Endpoint m[0]
        double m0 = ((2.0 * h[0] + h[1]) * d[0] - h[0] * d[1]) / (h[0] + h[1]);
        if (m0 * d[0] <= 0.0) m0 = 0.0;
        else if ((d[0] * d[1] < 0.0) && (fabs(m0) > 3.0 * fabs(d[0]))) m0 = 3.0 * d[0];
        m[0] = m0;
        // Endpoint m[n-1]
        double mn = ((2.0 * h[n-2] + h[n-3]) * d[n-2] - h[n-2] * d[n-3]) / (h[n-2] + h[n-3]);
        if (mn * d[n-2] <= 0.0) mn = 0.0;
        else if ((d[n-2] * d[n-3] < 0.0) && (fabs(mn) > 3.0 * fabs(d[n-2]))) mn = 3.0 * d[n-2];
        m[n-1] = mn;
    }

    // Build per-segment cubic coefficients in dx=(x-x_i):
    for (Py_ssize_t i = 0; i < nm1; ++i) {
        double H = h[i];
        double yi = y[i];
        double mi = m[i];
        double mip1 = m[i+1];
        // A and B helpers
        double A = (y[i+1] - yi - mi * H) / (H * H);
        double B = (mip1 - mi) / H;
        double a = (B - 2.0 * A) / H;
        double b = 3.0 * A - B;
        curve_points[i].a = a;
        curve_points[i].b = b;
        curve_points[i].c = mi;
        curve_points[i].d = yi;
    }

    // Assign to curve and free temps
    curve.length = (size_t)n;
    curve.points = curve_points;
    free(x);
    free(y);
    free(h);
    free(d);
    free(m);
    return curve;
}

#endif // BIND_H
