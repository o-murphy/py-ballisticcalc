#!/usr/bin/env python
"""setup.py script for py_ballisticcalc library"""
import os

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
    "cdivision": True, # use with caution! can affect on "/" operator
    "binding": False,  # Keep as False unless you explicitly want Python-level binding methods
    "c_api_binop_methods": True,
    "warn.undeclared": True,
    "warn.unreachable": True,
    "warn.maybe_uninitialized": True,
    "warn.unused": True,
    "warn.unused_arg": True,
    "warn.multiple_declarators": True,
    "show_performance_hints": True,
    # "emit_code_comments": False
}

ext_base_dir = 'py_ballisticcalc_exts'

# Define all C source files and their paths
C_SOURCES = {
    'v3d': os.path.join(ext_base_dir, 'src', 'v3d.c'),
    'bclib': os.path.join(ext_base_dir, 'src', 'bclib.c'),
    "bind": os.path.join(ext_base_dir, 'src', 'bind.c'),
    # Add any other C source files here
}

# Define dependencies for each extension as a dictionary
# Keys are extension names (as in extension_names list)
# Values are lists of C source file keys from C_SOURCES that they depend on.
EXTENSION_DEPS = {
    "cy_bindings": ["bclib", "bind"],
    "base_engine": ["v3d", "bclib"],
    "euler_engine": ["v3d", "bclib"],
    "rk4_engine": ["v3d", "bclib"],
    "trajectory_data": [], # No specific C dependencies listed beyond its own .pyx
}


# added 'include' to include_dirs for searching headers ***
include_dirs = [
    ext_base_dir,  # For .pxd files
    os.path.join(ext_base_dir, 'src'),
    os.path.join(ext_base_dir, 'include'),
]

# Initialize extensions list
extensions = []

# Dynamically create extensions for names in extension_names
for name, deps in EXTENSION_DEPS.items():
    # Start with the Cython .pyx file for the current extension
    sources = [os.path.join(ext_base_dir, name + '.pyx')]

    # Add dependent C source files from the EXTENSION_DEPS dictionary
    # Use .get(name, []) to safely get an empty list if an extension has no explicit C dependencies
    for dep_key in deps:
        if dep_key in C_SOURCES:
            sources.append(C_SOURCES[dep_key])
        else:
            print(f"Warning: C source '{dep_key}' not found in C_SOURCES dictionary for extension '{name}'.")


    extensions.append(
        Extension(
            'py_ballisticcalc_exts.' + name,
            sources=sources,
            include_dirs=include_dirs,
            # extra_compile_args=["-std=c99"], # Uncomment if needed for specific C standards
            # libraries=['m'] # For Linux/macOS, add 'm' for math functions. For Windows, usually not needed or part of default C runtime.
        )
    )

extensions = cythonize(extensions,
                       compiler_directives=compiler_directives,
                       annotate=True)

setup(ext_modules=extensions)
