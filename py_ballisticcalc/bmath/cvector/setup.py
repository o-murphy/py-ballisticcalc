from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension('vector', ['py_ballisticcalc/bmath/cvector/vector.pyx']),
    Extension('energy', ['py_ballisticcalc/bmath/cunit/energy.pyx']),
    Extension('temperature', ['py_ballisticcalc/bmath/cunit/temperature.pyx']),
    Extension('pressure', ['py_ballisticcalc/bmath/cunit/pressure.pyx']),
    Extension('velocity', ['py_ballisticcalc/bmath/cunit/velocity.pyx']),
    Extension('distance', ['py_ballisticcalc/bmath/cunit/distance.pyx']),
    Extension('angular', ['py_ballisticcalc/bmath/cunit/angular.pyx']),
    Extension('weight', ['py_ballisticcalc/bmath/cunit/weight.pyx']),
]
setup(
    ext_modules=cythonize(
        extensions, language_level=3, annotate=True)
)

