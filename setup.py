# Usage: python setup.py build_ext --inplace

from setuptools import setup, Extension
from Cython.Build import cythonize
from pathlib import Path

def iter_extensions(path):
    founded_extensions = []
    extensions_dir = Path(path).parent
    for ext_path in Path.iterdir(extensions_dir):
        if ext_path.suffix == '.pyx':
            ext_name = f"{'.'.join(extensions_dir.parts)}.{ext_path.stem}"
            ext = Extension(ext_name, [ext_path.as_posix()])
            founded_extensions.append(ext)
    return founded_extensions

extensions_paths = [
    'py_ballisticcalc/*.pyx',
    'py_ballisticcalc/bmath/unit/*.pyx',
    'py_ballisticcalc/bmath/vector/*.pyx',
]

extensions = []
for path in extensions_paths:
    extensions += iter_extensions(path)

compiler_directives = {"language_level": 3, "embedsignature": True}
extensions = cythonize(extensions, compiler_directives=compiler_directives)

setup(
    name='py_ballisticcalc',
    ext_modules=extensions,
)
