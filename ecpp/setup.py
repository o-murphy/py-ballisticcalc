from setuptools import setup, Extension
from Cython.Build import cythonize

# Define the extension module
extensions = [
    Extension(
        "v3d",
        # Source files: Cython wrapper and C++ implementation
        sources=["ecpp/v3d.pyx", "ecpp/src/v3d.cpp"],
        include_dirs=["ecpp/src", "ecpp/include"],
        language="c++",
        # Compiler flags for C++11 (or later) are usually required for Cython C++
        extra_compile_args=["-std=c++11"], 
    ),
    Extension(
        "v3dc",
        # Source files: Cython wrapper and C++ implementation
        sources=["ecpp/v3dc.pyx", "ecpp/src/v3d.c"],
        include_dirs=["ecpp/src", "ecpp/include"],
        language="c",
        # Compiler flags for C++11 (or later) are usually required for Cython C++
        extra_compile_args=["-std=c++11"], 
    )
]

setup(
    name='ecpp',
    ext_modules=cythonize(extensions, annotate=True),
)