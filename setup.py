#!/usr/bin/env python
import io
import os
import re
from pathlib import Path

from setuptools import setup, find_packages, Extension

try:
    from Cython.Build import cythonize

    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False


def read(*names, **kwargs):
    try:
        with io.open(
                os.path.join(os.path.dirname(__file__), *names),
                encoding=kwargs.get("encoding", "utf8")
        ) as fp:
            return fp.read()
    except IOError:
        return ''


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


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


# extensions_paths = [
#     Extension('*', ['py_ballisticcalc/*.pyx']),
#     Extension('*', ['py_ballisticcalc/bmath/unit/*.pyx']),
#     Extension('*', ['py_ballisticcalc/bmath/vector/*.pyx']),
# ]

extensions_paths = [
    'py_ballisticcalc/*.pyx',
    'py_ballisticcalc/bmath/unit/*.pyx',
    'py_ballisticcalc/bmath/vector/*.pyx',
]

extensions = []
for path in extensions_paths:
    extensions += iter_extensions(path)

# CYTHONIZE = bool(int(os.getenv("CYTHONIZE", 0))) and use_cython is not None

# if CYTHONIZE:
if USE_CYTHON:
    compiler_directives = {"language_level": 3, "embedsignature": True}
    extensions = cythonize(extensions, compiler_directives=compiler_directives)
else:
    extensions = no_cythonize(extensions)

with open("requirements.txt") as fp:
    install_requires = fp.read().strip().split("\n")
    print(install_requires)

with open("requirements-dev.txt") as fp:
    dev_requires = fp.read().strip().split("\n")

setup(

    name='py_ballisticcalc',
    ext_modules=extensions,
    install_requires=install_requires,
    setup_requires=[
        'setuptools>=18.0',  # automatically handles Cython extensions
        'cython>=3.0.0a10',
    ],

    extras_require={
        "dev": dev_requires,
        "docs": ["sphinx", "sphinx-rtd-theme"]
    },

    version=find_version('py_ballisticcalc', '__init__.py'),
    url='https://github.com/o-murphy/py_ballisticcalc',
    download_url='https://pypi.python.org/pypi/py_ballisticcalc/',
    project_urls={
        "Homepage": 'https://github.com/o-murphy/py_ballisticcalc',
        "Code": 'https://github.com/o-murphy/py_ballisticcalc',
        "Documentation": 'https://github.com/o-murphy/py_ballisticcalc',
        "Bug Tracker": 'https://github.com/o-murphy/py_ballisticcalc/issues'
    },
    license='LGPL-3.0',
    author="o-murphy",
    author_email='thehelixpg@gmail.com',
    description='LGPL library for small arms ballistic calculations (Python 3)',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    zip_safe=True,
    py_modules=find_packages() + [
        'py_ballisticcalc.drag_tables',
        'py_ballisticcalc.bin_test',
        'py_ballisticcalc.bmath.unit.unit_test',
        'py_ballisticcalc.bmath.vector.vector_test',
    ],
)
