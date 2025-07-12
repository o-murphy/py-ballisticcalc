#ifndef BIND_H
#define BIND_H

#include <Python.h>
#include "bclib.h"  // MachList_t typedef must be here

Config_t Config_t_fromPyObject(PyObject* config);
MachList_t MachList_t_fromPylist(PyObject *pylist);
Curve_t Curve_t_fromPylist(PyObject *data_points);
//Wind_t Wind_t_fromPythonObj(PyObject *w);

#endif // BIND_H
