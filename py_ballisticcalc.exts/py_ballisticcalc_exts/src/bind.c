#ifndef BIND_H
#define BIND_H

#include <Python.h>
#include <stdlib.h>
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
    Py_ssize_t len = PyList_Size(data_points);
    if (len < 2)  // треба принаймні 2 точки для коректної інтерполяції
        return curve;

    CurvePoint_t *curve_points = (CurvePoint_t *) malloc(len * sizeof(CurvePoint_t));
    if (!curve_points)
        return curve;

    curve.length = (size_t)len;
    curve.points = curve_points;

    // Локальні змінні для розрахунку
    double rate, x1, x2, x3, y1, y2, y3, a, b, c;

    // Функція для отримання атрибутів з Python-об’єкту:
    // mach = PyFloat_AsDouble(PyObject_GetAttrString(obj, "Mach"))
    // cd = PyFloat_AsDouble(PyObject_GetAttrString(obj, "CD"))

    // Перша точка (спеціальний випадок)
    PyObject *item0 = PyList_GetItem(data_points, 0); // borrowed ref
    PyObject *item1 = PyList_GetItem(data_points, 1);

    double mach0 = PyFloat_AsDouble(PyObject_GetAttrString(item0, "Mach"));
    double cd0 = PyFloat_AsDouble(PyObject_GetAttrString(item0, "CD"));
    double mach1 = PyFloat_AsDouble(PyObject_GetAttrString(item1, "Mach"));
    double cd1 = PyFloat_AsDouble(PyObject_GetAttrString(item1, "CD"));

    rate = (cd1 - cd0) / (mach1 - mach0);
    curve_points[0].a = 0.0;
    curve_points[0].b = rate;
    curve_points[0].c = cd0 - mach0 * rate;

    // Основний цикл, інтерполяція для точок 1..len-2
    for (Py_ssize_t i = 1; i < len - 1; i++) {
        PyObject *item_m1 = PyList_GetItem(data_points, i - 1);
        PyObject *item_i = PyList_GetItem(data_points, i);
        PyObject *item_p1 = PyList_GetItem(data_points, i + 1);

        x1 = PyFloat_AsDouble(PyObject_GetAttrString(item_m1, "Mach"));
        x2 = PyFloat_AsDouble(PyObject_GetAttrString(item_i, "Mach"));
        x3 = PyFloat_AsDouble(PyObject_GetAttrString(item_p1, "Mach"));

        y1 = PyFloat_AsDouble(PyObject_GetAttrString(item_m1, "CD"));
        y2 = PyFloat_AsDouble(PyObject_GetAttrString(item_i, "CD"));
        y3 = PyFloat_AsDouble(PyObject_GetAttrString(item_p1, "CD"));

        double denom = ((x3*x3 - x1*x1)*(x2 - x1) - (x2*x2 - x1*x1)*(x3 - x1));
        if (denom == 0) {
            // Уникаємо ділення на 0, можна задати дефолтні значення або помилку
            a = 0;
            b = 0;
            c = y2;  // Просто константа
        } else {
            a = ((y3 - y1)*(x2 - x1) - (y2 - y1)*(x3 - x1)) / denom;
            b = (y2 - y1 - a*(x2*x2 - x1*x1)) / (x2 - x1);
            c = y1 - (a*x1*x1 + b*x1);
        }
        curve_points[i].a = a;
        curve_points[i].b = b;
        curve_points[i].c = c;
    }

    // Остання точка (спеціальний випадок)
    PyObject *item_last = PyList_GetItem(data_points, len - 1);
    PyObject *item_before_last = PyList_GetItem(data_points, len - 2);

    double mach_last = PyFloat_AsDouble(PyObject_GetAttrString(item_last, "Mach"));
    double cd_last = PyFloat_AsDouble(PyObject_GetAttrString(item_last, "CD"));
    double mach_before_last = PyFloat_AsDouble(PyObject_GetAttrString(item_before_last, "Mach"));
    double cd_before_last = PyFloat_AsDouble(PyObject_GetAttrString(item_before_last, "CD"));

    rate = (cd_last - cd_before_last) / (mach_last - mach_before_last);
    curve_points[len - 1].a = 0.0;
    curve_points[len - 1].b = rate;
    curve_points[len - 1].c = cd_last - mach_before_last * rate;

    return curve;
}

//Wind_t Wind_t_fromPythonObj(PyObject *w) {
//    Wind_t wind = {0.0, 0.0, 0.0, 0.0};
//
//    if (!w) return wind;
//
//    // Отримуємо velocity._fps
//    PyObject *velocity = PyObject_GetAttrString(w, "velocity");
//    if (!velocity) return wind;
//    PyObject *velocity_fps = PyObject_GetAttrString(velocity, "_fps");
//    Py_DECREF(velocity);
//    if (!velocity_fps) return wind;
//    double velocity_val = PyFloat_AsDouble(velocity_fps);
//    Py_DECREF(velocity_fps);
//    if (PyErr_Occurred()) return wind;
//
//    // direction_from._rad
//    PyObject *direction_from = PyObject_GetAttrString(w, "direction_from");
//    if (!direction_from) return wind;
//    PyObject *direction_rad = PyObject_GetAttrString(direction_from, "_rad");
//    Py_DECREF(direction_from);
//    if (!direction_rad) return wind;
//    double direction_val = PyFloat_AsDouble(direction_rad);
//    Py_DECREF(direction_rad);
//    if (PyErr_Occurred()) return wind;
//
//    // until_distance._feet
//    PyObject *until_distance = PyObject_GetAttrString(w, "until_distance");
//    if (!until_distance) return wind;
//    PyObject *until_feet = PyObject_GetAttrString(until_distance, "_feet");
//    Py_DECREF(until_distance);
//    if (!until_feet) return wind;
//    double until_val = PyFloat_AsDouble(until_feet);
//    Py_DECREF(until_feet);
//    if (PyErr_Occurred()) return wind;
//
//    // MAX_DISTANCE_FEET (прямий атрибут)
//    PyObject *max_distance = PyObject_GetAttrString(w, "MAX_DISTANCE_FEET");
//    if (!max_distance) return wind;
//    double max_distance_val = PyFloat_AsDouble(max_distance);
//    Py_DECREF(max_distance);
//    if (PyErr_Occurred()) return wind;
//
//    wind.velocity = velocity_val;
//    wind.direction_from = direction_val;
//    wind.until_distance = until_val;
//    wind.MAX_DISTANCE_FEET = max_distance_val;
//
//    return wind;
//}

#endif // BIND_H
