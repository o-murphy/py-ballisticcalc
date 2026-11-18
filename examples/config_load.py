from py_ballisticcalc import (basicConfig, PreferredUnits, loadMixedUnits)

import importlib.resources

# with importlib.resources.as_file(importlib.resources.files('py_ballisticcalc').joinpath('.pybc.toml')) as config_file:
#     basicConfig(config_file)

# files() returns a Traversable, not a context manager (a Path stopped being one in Python 3.13): as_file() is.
with importlib.resources.as_file(
        importlib.resources.files('py_ballisticcalc').joinpath('assets/.pybc-imperial.toml')) as config_file:
    basicConfig(config_file)

print("Imperial:")
print(PreferredUnits)

print()

loadMixedUnits()

print("Mixed:")
print(PreferredUnits)