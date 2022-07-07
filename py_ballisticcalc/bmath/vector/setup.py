from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [Extension('vector', ['py_ballisticcalc/bmath/vector/vector.py'])]
setup(
    ext_modules=cythonize(
        extensions, language_level=3, annotate=True)
)

