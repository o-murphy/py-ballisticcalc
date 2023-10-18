#!/usr/bin/env python

"""setup.py script for py_ballisticcalc library"""

import os
from pathlib import Path

from setuptools import setup, Extension

try:
    from Cython.Build import cythonize

    # USE_CYTHON = True
except ImportError:
    # USE_CYTHON = False
    cythonize = False


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
            ext = Extension(ext_name, [ext_path.as_posix()])
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
    compiler_directives = {"language_level": 3, "embedsignature": True}
    extensions = cythonize(extensions, compiler_directives=compiler_directives)
else:
    extensions = no_cythonize(extensions)

setup(
    ext_modules=extensions,
)
