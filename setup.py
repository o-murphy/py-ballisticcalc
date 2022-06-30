#!/usr/bin/env python
import sys
import py_ballisticcalc

from setuptools import setup, find_packages

setup(
    name='py_ballisticcalc',
    version=py_ballisticcalc.__version__,
    packages=find_packages(),
    url='https://github.com/o-murphy/py_ballisticcalc',
    download_url='http://pypi.python.org/pypi/py_ballisticcalc/',
    license='LGPL-3.0',
    author=py_ballisticcalc.__author__,
    author_email='thehelixpg@gmail.com',
    description='LGPL library for small arms ballistic calculations (Python 3)',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    zip_safe=True,
    py_modules=['py_ballisticcalc'],
    requirements=[]
)
