#!/usr/bin/env python
"""setup.py script for py_ballisticcalc library"""
import os

from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
except ImportError:
    import sys
    setup()
    sys.exit(0)

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

ext_base_dir = 'py_ballisticcalc_exts'

# Define paths for common C source files
V3D_C_SOURCE = os.path.join(ext_base_dir, 'src', 'v3d.c')
HELPERS_C_SOURCE = os.path.join(ext_base_dir, 'src', 'helpers.c')
# If you add tflag.c or tdatafilter.c, define them here:
# TFLAG_C_SOURCE = os.path.join(ext_base_dir, 'src', 'tflag.c')
# TDATAFILTER_C_SOURCE = os.path.join(ext_base_dir, 'src', 'tdatafilter.c')

# *** NEW: Define dependencies using a dictionary ***
# Keys are the extension names (without 'py_ballisticcalc_exts.'),
# values are lists of additional C source files they depend on.
extension_dependencies = {
    "cy_bindings": [],
    "base_engine": [V3D_C_SOURCE, HELPERS_C_SOURCE],
    "euler_engine": [V3D_C_SOURCE],
    "rk4_engine": [V3D_C_SOURCE],
    "trajectory_data": [], # Add relevant C sources here if trajectory_data needs them
}

# The overall list of extension names to build (keys from the dictionary)
extension_names_to_build = list(extension_dependencies.keys())

# Include directories
include_dirs = [
    ext_base_dir,
    os.path.join(ext_base_dir, 'src'),
    os.path.join(ext_base_dir, 'include'),
]

# Initialize extensions list
extensions = []

# Dynamically create extensions based on the dependency dictionary
for name in extension_names_to_build:
    # Start with the primary Cython source file
    sources = [os.path.join(ext_base_dir, name + '.pyx')]

    # Add C dependencies from the dictionary
    sources.extend(extension_dependencies[name])

    extensions.append(
        Extension(
            'py_ballisticcalc_exts.' + name,
            sources=sources,
            include_dirs=include_dirs,
            extra_compile_args=[
                # "-std=c99",
                # "-Wall"
            ], # Uncomment if needed
            # libraries=['m'] # Uncomment if needed for math functions
        )
    )

extensions = cythonize(extensions,
                       compiler_directives=compiler_directives,
                       annotate=True)

setup(ext_modules=extensions)
