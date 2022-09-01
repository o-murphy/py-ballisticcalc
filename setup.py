#!/usr/bin/env python
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
import py_ballisticcalc

extensions = [
    Extension('*', ['py_ballisticcalc/*.pyx']),
    Extension('*', ['py_ballisticcalc/bmath/unit/*.pyx']),
    Extension('*', ['py_ballisticcalc/bmath/vector/*.pyx']),
    # Extension('*', ['py_ballisticcalc/__init__.py']),
    # Extension('*', ['py_ballisticcalc/bmath/unit/__init__.py']),
    # Extension('*', ['py_ballisticcalc/bmath/vector/__init__.py']),
]

setup(
    ext_modules=cythonize(
        extensions,
        language_level=3,
        # annotate=True,
    ),
    name='py_ballisticcalc',
    version=py_ballisticcalc.__version__,
    packages=find_packages(),
    url='https://github.com/o-murphy/py_ballisticcalc',
    download_url='http://pypi.python.org/pypi/py_ballisticcalc/',
    license='LGPL-3.0',
    author=py_ballisticcalc.__author__,
    author_email='thehelixpg@gmail.com',
    description='LGPL library for small arms ballistic calculations (Python 3)',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    zip_safe=True,
    py_modules=['py_ballisticcalc'],
)
