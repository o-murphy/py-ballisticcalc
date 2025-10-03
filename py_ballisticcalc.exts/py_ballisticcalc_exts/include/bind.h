#ifndef BIND_H
#define BIND_H

#include <Python.h>
#include "bclib.h"  // MachList_t typedef must be here

Config_t Config_t_fromPyObject(const PyObject* config);
MachList_t MachList_t_fromPylist(const PyObject *pylist);
Curve_t Curve_t_fromPylist(const PyObject *data_points);
Wind_t Wind_t_fromPyObject(PyObject *w);

#endif // BIND_H
