#!/usr/bin/env python
import os
from pathlib import Path

from setuptools import setup, Extension

try:
    from Cython.Build import cythonize

    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False


def iter_extensions(path):
    founded_extensions = []
    extensions_dir = Path(path).parent
    for ext_path in Path.iterdir(extensions_dir):
        if ext_path.suffix == '.pyx':
            ext_name = f"{'.'.join(extensions_dir.parts)}.{ext_path.stem}"
            ext = Extension(ext_name, [ext_path.as_posix()])
            founded_extensions.append(ext)
    return founded_extensions


def no_cythonize(extensions, **_ignore):
    for extension in extensions:
        sources = []
        for sfile in extension.sources:
            path, ext = os.path.splitext(sfile)

            if ext in (".pyx", ".py"):
                if extension.language == "c++":
                    ext = ".cpp"
                else:
                    ext = ".c"
                sfile = path + ext
            sources.append(sfile)
        extension.sources[:] = sources
    return extensions


extensions_paths = [
    'py_ballisticcalc/*.pyx',
]

extensions = []
for path in extensions_paths:
    extensions += iter_extensions(path)

if USE_CYTHON:
    compiler_directives = {"language_level": 3, "embedsignature": True}
    extensions = cythonize(extensions, compiler_directives=compiler_directives)
else:
    extensions = no_cythonize(extensions)

setup(
    ext_modules=extensions,
)
