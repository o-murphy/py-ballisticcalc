from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension('vector', ['py_ballisticcalc/lib/bmath/vector/vector.pyx']),
    Extension('energy', ['py_ballisticcalc/lib/bmath/unit/energy.pyx']),
    Extension('temperature', ['py_ballisticcalc/lib/bmath/unit/temperature.pyx']),
    Extension('pressure', ['py_ballisticcalc/lib/bmath/unit/pressure.pyx']),
    Extension('velocity', ['py_ballisticcalc/lib/bmath/unit/velocity.pyx']),
    Extension('distance', ['py_ballisticcalc/lib/bmath/unit/distance.pyx']),
    Extension('angular', ['py_ballisticcalc/lib/bmath/unit/angular.pyx']),
    Extension('weight', ['py_ballisticcalc/lib/bmath/unit/weight.pyx']),
    Extension('atmosphere', ['py_ballisticcalc/lib/atmosphere.pyx']),
    Extension('shot_parameters', ['py_ballisticcalc/lib/shot_parameters.pyx']),
    Extension('drag', ['py_ballisticcalc/lib/drag.pyx']),
    Extension('projectile', ['py_ballisticcalc/lib/projectile.pyx']),
    Extension('trajectory_calculator', ['py_ballisticcalc/lib/trajectory_calculator.pyx']),
    Extension('trajectory_data', ['py_ballisticcalc/lib/trajectory_data.pyx']),
    Extension('weapon', ['py_ballisticcalc/lib/weapon.pyx']),
    Extension('wind', ['py_ballisticcalc/lib/wind.pyx']),
    Extension('multiple_bc', ['py_ballisticcalc/lib/tools/multiple_bc.pyx']),
    Extension('profile', ['py_ballisticcalc/lib/profile.pyx']),
    Extension('drag_tables', ['py_ballisticcalc/lib/drag_tables.pyx']),
]

setup(
    ext_modules=cythonize(
        extensions, language_level=3,
        # annotate=True,
    )
)
