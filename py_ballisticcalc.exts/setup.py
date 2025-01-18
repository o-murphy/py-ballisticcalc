#!/usr/bin/env python
"""setup.py script for py_ballisticcalc library"""
from setuptools import setup, Extension
try:
    from Cython.Build import cythonize
except ImportError:
    import sys
    # use this command to skip building wheel and compiling modules on unsupported platforms
    # pip install --no-build-isolation --no-binary :all: py-ballisticcalc.exts
    setup()
    sys.exit(0)  # Stop installation


compiler_directives = {
    "language_level": 3,
    "embedsignature": True,
    "cdivision": True,
    "binding": False,
    "c_api_binop_methods": True,
    "warn.undeclared": True,
    "warn.unreachable": True,
    "warn.maybe_uninitialized": True,
    "warn.unused": True,
    "warn.unused_arg": True,
    "warn.multiple_declarators": True,
    "show_performance_hints": True,
}

extension_names = [
    "vector",
    "trajectory_calc",
    "trajectory_data",
    "cy_euler",
]

extensions = [
    Extension('py_ballisticcalc_exts.' + name,
              ['py_ballisticcalc_exts/' + name + '.pyx'])
    for name in extension_names
]

extensions = cythonize(extensions,
                       compiler_directives=compiler_directives,
                       annotate=True)

setup(ext_modules=extensions)
