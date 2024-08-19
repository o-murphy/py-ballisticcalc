# #!/usr/bin/env python

"""setup.py script for py_ballisticcalc library"""

import warnings

from setuptools import setup
from mypyc.build import mypycify

from distutils import ccompiler
from distutils.errors import DistutilsError


def check_compiler():
    try:
        comp = ccompiler.new_compiler(dry_run=True)
        comp.compile([])
        return True
    except DistutilsError as err:
        warnings.warn("Can't compile c-extension due to: {err}")
        warnings.warn("Continue installation in pure python mode")
        return False


setup(
    ext_modules=mypycify(
        [
            'py_ballisticcalc/',
            '--exclude',
            'py_ballisticcalc/__init__.py',
            '--exclude',
            'py_ballisticcalc/unit.py',
            '--exclude',
            'py_ballisticcalc/conditions.py',
            '--exclude',
            'py_ballisticcalc/munition.py',
            '--exclude',
            'py_ballisticcalc/trajectory_data.py',
            '--exclude',
            'py_ballisticcalc/example.py'
        ],
    ) if check_compiler() else None
)
