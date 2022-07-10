from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [Extension('calculate_by_curve', ['py_ballisticcalc/extended/c_modules/calculate_by_curve.py'])]
setup(
    ext_modules=cythonize(
        extensions, language_level=3, annotate=True)
)