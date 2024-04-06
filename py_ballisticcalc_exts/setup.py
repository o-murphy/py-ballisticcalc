#!/usr/bin/env python

"""setup.py script for py_ballisticcalc library"""

import os
from pathlib import Path

from setuptools import setup, Extension
# import numpy

try:
    from Cython.Build import cythonize

    # USE_CYTHON = True
except ImportError:
    # USE_CYTHON = False
    cythonize = False



compiler_directives = {
    "language_level": 3,
    "embedsignature": True,
    "cdivision": True,
    "binding": False,
    "c_api_binop_methods": True,
    # "embedsignature.format": 'python'
    # "annotation_typing": False,
    # "cpp_locals": True
    # "optimize.use_switch": True,
    # "optimize.unpack_method_calls": False
    "warn.undeclared": True,
    "warn.unreachable": True,
    "warn.maybe_uninitialized": True,
    "warn.unused": True,
    "warn.unused_arg": True,
    # "warn.unused_result": True,
    "warn.multiple_declarators": True,
    "show_performance_hints": True,
}

extra_compile_args = [
    # "-CYTHON_USE_TYPE_SLOTS=1",
    # "-CYTHON_USE_PYTYPE_LOOKUP=1",
    # "-CYTHON_AVOID_BORROWED_REFS=1",
    # "-CYTHON_USE_PYLONG_INTERNALS=1",
    # "-CYTHON_USE_PYLIST_INTERNALS=1",
    # "-CYTHON_USE_UNICODE_INTERNALS=1",
    # "-CYTHON_FAST_GIL=1",
    # "-CYTHON_UNPACK_METHODS=1",
    # "-CYTHON_USE_DICT_VERSIONS=1",
]


def iter_extensions(path) -> list:
    """
    iterate extensions in project directory
    :rtype: list
    :return: list of extensions paths
    """
    founded_extensions = []
    extensions_dir = Path(path).parent
    for ext_path in Path.iterdir(extensions_dir):
        if ext_path.suffix == '.pyx':
            ext_name = f"{'.'.join(extensions_dir.parts)}.{ext_path.stem}"
            ext = Extension(ext_name,
                            [ext_path.as_posix()],
                            extra_compile_args=extra_compile_args,
                            # include_dirs=[numpy.get_include()]
                            )
            founded_extensions.append(ext)
    return founded_extensions


def no_cythonize(exts, **_ignore):
    """grep extensions sources without cythonization"""
    for extension in exts:
        sources = []
        for src_file in extension.sources:
            path, ext = os.path.splitext(src_file)

            if ext in (".pyx", ".py"):
                if extension.language == "c++":
                    ext = ".cpp"
                else:
                    ext = ".c"
                src_file = path + ext
            sources.append(src_file)
        extension.sources[:] = sources
    return exts


extensions_paths = [
    'py_ballisticcalc_exts/*.pyx',
]

extensions = []
for path_ in extensions_paths:
    extensions += iter_extensions(path_)

if cythonize:
    extensions = cythonize(extensions,
                           compiler_directives=compiler_directives,
                           annotate=True)
else:
    extensions = no_cythonize(extensions)

setup(
    ext_modules=extensions,
)
