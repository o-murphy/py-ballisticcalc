#!/usr/bin/env python

"""setup.py script for py_ballisticcalc library"""

from mypyc.build import mypycify
from setuptools import setup

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
        ]
    )
)
