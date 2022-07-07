from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [Extension('c_trajectory_calculator_no_annotate', ['c_trajectory_calculator_no_annotate.py'])]
setup(
    ext_modules=cythonize(
        extensions, language_level=3)
)
