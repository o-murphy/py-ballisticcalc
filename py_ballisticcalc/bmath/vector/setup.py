from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [Extension('cvector', ['py_ballisticcalc/bmath/vector/cvector.pyx'])]
setup(
    ext_modules=cythonize(
        extensions, language_level=3, annotate=True)
)

