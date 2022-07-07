from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [Extension('tjcalc', ['py_ballisticcalc/extended/tjcalc.py'])]
setup(
    ext_modules=cythonize(
        extensions, language_level=3)
)

