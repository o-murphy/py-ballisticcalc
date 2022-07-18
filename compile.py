#!/usr/bin/env python
from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize

import sys
import py_ballisticcalc

from setuptools import setup, find_packages

extensions = [
    Extension('py_ballisticcalc.lib.bmath.vector.vector', ['py_ballisticcalc/lib/bmath/vector/vector.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.energy', ['py_ballisticcalc/lib/bmath/unit/energy.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.temperature', ['py_ballisticcalc/lib/bmath/unit/temperature.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.pressure', ['py_ballisticcalc/lib/bmath/unit/pressure.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.velocity', ['py_ballisticcalc/lib/bmath/unit/velocity.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.distance', ['py_ballisticcalc/lib/bmath/unit/distance.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.angular', ['py_ballisticcalc/lib/bmath/unit/angular.pyx']),
    Extension('py_ballisticcalc.lib.bmath.unit.weight', ['py_ballisticcalc/lib/bmath/unit/weight.pyx']),
    Extension('py_ballisticcalc.lib.atmosphere', ['py_ballisticcalc/lib/atmosphere.pyx']),
    Extension('py_ballisticcalc.lib.shot_parameters', ['py_ballisticcalc/lib/shot_parameters.pyx']),
    Extension('py_ballisticcalc.lib.drag', ['py_ballisticcalc/lib/drag.pyx']),
    Extension('py_ballisticcalc.lib.projectile', ['py_ballisticcalc/lib/projectile.pyx']),
    Extension('py_ballisticcalc.lib.trajectory_calculator', ['py_ballisticcalc/lib/trajectory_calculator.pyx']),
    Extension('py_ballisticcalc.lib.trajectory_data', ['py_ballisticcalc/lib/trajectory_data.pyx']),
    Extension('py_ballisticcalc.lib.weapon', ['py_ballisticcalc/lib/weapon.pyx']),
    Extension('py_ballisticcalc.lib.wind', ['py_ballisticcalc/lib/wind.pyx']),
    Extension('py_ballisticcalc.lib.tools.multiple_bc', ['py_ballisticcalc/lib/tools/multiple_bc.pyx']),
    Extension('py_ballisticcalc.lib.profile', ['py_ballisticcalc/lib/profile.pyx']),
    Extension('py_ballisticcalc.lib.drag_tables', ['py_ballisticcalc/lib/drag_tables.pyx']),
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
    requirements=[],
    # include_package_data=True,
    # package_data={'profile': ['py_ballisticcalc/lib/profile.cp39-win_amd64.pyd']}
)
