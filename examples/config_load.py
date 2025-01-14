from py_ballisticcalc import (basicConfig, PreferredUnits, loadMixedUnits)

import importlib.resources

# with importlib.resources.files('py_ballisticcalc').joinpath('.pybc.toml') as config_file:
#     basicConfig(config_file)

with importlib.resources.files('py_ballisticcalc').joinpath('assets/.pybc-imperial.toml') as config_file:
    basicConfig(config_file)

print("Imperial:")
print(PreferredUnits)

print()

loadMixedUnits()

print("Mixed:")
print(PreferredUnits)