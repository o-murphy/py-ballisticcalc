#!/usr/bin/env python
from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize

import sys
import py_ballisticcalc

from setuptools import setup, find_packages

extensions = [
    Extension('py_ballisticcalc.bmath.vector.vector', ['py_ballisticcalc/bmath/vector/vector.pyx']),
    Extension('py_ballisticcalc.bmath.unit.energy', ['py_ballisticcalc/bmath/unit/energy.pyx']),
    Extension('py_ballisticcalc.bmath.unit.temperature', ['py_ballisticcalc/bmath/unit/temperature.pyx']),
    Extension('py_ballisticcalc.bmath.unit.pressure', ['py_ballisticcalc/bmath/unit/pressure.pyx']),
    Extension('py_ballisticcalc.bmath.unit.velocity', ['py_ballisticcalc/bmath/unit/velocity.pyx']),
    Extension('py_ballisticcalc.bmath.unit.distance', ['py_ballisticcalc/bmath/unit/distance.pyx']),
    Extension('py_ballisticcalc.bmath.unit.angular', ['py_ballisticcalc/bmath/unit/angular.pyx']),
    Extension('py_ballisticcalc.bmath.unit.weight', ['py_ballisticcalc/bmath/unit/weight.pyx']),
    Extension('py_ballisticcalc.atmosphere', ['py_ballisticcalc/atmosphere.pyx']),
    Extension('py_ballisticcalc.shot_parameters', ['py_ballisticcalc/shot_parameters.pyx']),
    Extension('py_ballisticcalc.drag', ['py_ballisticcalc/drag.pyx']),
    Extension('py_ballisticcalc.projectile', ['py_ballisticcalc/projectile.pyx']),
    Extension('py_ballisticcalc.trajectory_calculator', ['py_ballisticcalc/trajectory_calculator.pyx']),
    Extension('py_ballisticcalc.trajectory_data', ['py_ballisticcalc/trajectory_data.pyx']),
    Extension('py_ballisticcalc.weapon', ['py_ballisticcalc/weapon.pyx']),
    Extension('py_ballisticcalc.wind', ['py_ballisticcalc/wind.pyx']),
    Extension('py_ballisticcalc.multiple_bc', ['py_ballisticcalc/multiple_bc.pyx']),
    Extension('py_ballisticcalc.profile', ['py_ballisticcalc/profile.pyx']),
    Extension('py_ballisticcalc.drag_tables', ['py_ballisticcalc/drag_tables.pyx']),

    # Extension('py_ballisticcalc.__init__', ['py_ballisticcalc/__init__.py']),
]

# setup(
#     ext_modules=cythonize(
#         extensions, language_level=3,
#         # annotate=True,
#     )
# )

setup(
    ext_modules=cythonize(
        extensions, language_level=3,
        # force=True,
        # annotate=True,
    ),

    name='py_ballisticcalc',
    version=py_ballisticcalc.__version__,
    packages=find_packages(),
    # packages=['py_ballisticcalc'],
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
