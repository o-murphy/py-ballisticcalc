%module bcswig
%{
#include <stdint.h>
#include "bclibc/ffi/bclibc_ffi.h"
static PyObject *bc_bytes(const void *p, long n) { return PyBytes_FromStringAndSize((const char *)p, n); }
static double *bc_dptr(unsigned long long addr) { return (double *)(uintptr_t)addr; }
%}
%include <stdint.i>
%include <cpointer.i>
%include <carrays.i>
%pointer_functions(double, doublep)
%pointer_functions(int32_t, int32p)
%pointer_functions(BCLIBCFFI_TrajectoryData *, trajpp)
%pointer_functions(BCLIBCFFI_BaseTrajData *, basepp)
%array_class(BCLIBCFFI_Wind, WindArray)
PyObject *bc_bytes(const void *p, long n);
double *bc_dptr(unsigned long long addr);
%include "header_pp.h"
