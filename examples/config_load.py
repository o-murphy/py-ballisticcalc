from py_ballisticcalc import (basicConfig, PreferredUnits, loadMixedUnits,
                              get_global_use_powder_sensitivity, get_global_max_calc_step_size)

import importlib.resources

# with importlib.resources.files('py_ballisticcalc').joinpath('.pybc.toml') as config_file:
#     basicConfig(config_file)

with importlib.resources.files('py_ballisticcalc').joinpath('assets/.pybc-imperial.toml') as config_file:
    basicConfig(config_file)

print("Imperial:")
print(PreferredUnits)
print(get_global_use_powder_sensitivity())
print(get_global_max_calc_step_size())

print()

loadMixedUnits()

print("Mixed:")
print(PreferredUnits)
print(get_global_use_powder_sensitivity())
print(get_global_max_calc_step_size())