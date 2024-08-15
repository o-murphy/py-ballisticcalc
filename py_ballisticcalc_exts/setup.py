#!/usr/bin/env python
"""setup.py script for py_ballisticcalc library"""

from setuptools import setup, Extension
from Cython.Build import cythonize

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

extensions = [
    Extension('py_ballisticcalc_exts.trajectory_calc',
              ['py_ballisticcalc_exts/trajectory_calc.pyx'])
]

extensions = cythonize(extensions,
                       compiler_directives=compiler_directives,
                       annotate=True)

setup(ext_modules=extensions)
