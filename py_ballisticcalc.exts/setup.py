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
}

extension_names = [
    # "vector", # Temporary disabled
    # "v3d", not needed, there are just pxd header
    "cy_bindings",
    "base_engine",
    "euler_engine",
    "rk4_engine",  # Commented out as in your previous setup.py
    "trajectory_data",
]

ext_base_dir = 'py_ballisticcalc_exts'
# Тепер v3d.c знаходиться у src/
v3d_c_source = os.path.join(ext_base_dir, 'src', 'v3d.c')
v3d_c_dependent = [
    "base_engine",
    "euler_engine",
    "rk4_engine",
]

helpers_c_source = os.path.join(ext_base_dir, 'src', 'helpers.c')
helpers_c_dependent = [
    "base_engine",
]

# *** ЗМІНА ТУТ: Додано 'include' до include_dirs для пошуку v3d.h ***
include_dirs = [
    ext_base_dir,  # Для .pxd файлів
    os.path.join(ext_base_dir, 'src'),  # Для .h файлів, якщо вони є у src/ (або якщо .pxd там)
    os.path.join(ext_base_dir, 'include'),  # Це головне: для v3d.h та інших C-заголовків
]

# Initialize extensions list
extensions = []

# FIXME: the explicit v3dw.pyx realisation not needed for cimport from v3dw.pxd
# Add the v3dw extension first, as it's a core dependency
# extensions.append(
#     Extension(
#         "py_ballisticcalc_exts.v3dw",  # Full module path: py_ballisticcalc_exts.v3dw
#         sources=[os.path.join(ext_base_dir, "include", "v3dw.pyx"), v3d_c_source],
#         # Include the directory where v3d.h and v3dw.pxd are located
#         include_dirs=[ext_base_dir],
#         extra_compile_args=["-std=c99"],
#         libraries=[],  # No explicit libraries needed here for v3d.c beyond default system libs (e.g., math)
#         extra_link_args=[]
#     )
# )

# Dynamically create extensions for names in extension_names
for name in extension_names:
    sources = [os.path.join(ext_base_dir, name + '.pyx')]

    # Add v3d.c to the sources for any extension that directly uses V3dT C functions
    if name in v3d_c_dependent:
        sources.append(v3d_c_source)

    if name in helpers_c_dependent:
        sources.append(helpers_c_source)

    extensions.append(
        Extension(
            'py_ballisticcalc_exts.' + name,
            sources=sources,
            # Ensure include_dirs is set for all extensions that use v3d.h
            include_dirs=include_dirs,  # Використовуємо оновлений include_dirs
            # extra_compile_args=["-std=c99"],
            # If these modules link to other specific libraries (e.g., -lm for math),
            # they should be added here.
            # libraries=['m'] # For Linux/macOS, add 'm' for math functions. For Windows, usually not needed or part of default C runtime.
        )
    )

extensions = cythonize(extensions,
                       compiler_directives=compiler_directives,
                       annotate=True)

setup(ext_modules=extensions)
