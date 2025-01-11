from py_ballisticcalc import (basicConfig, PreferredUnits,
                              get_global_use_powder_sensitivity, get_global_max_calc_step_size)

basicConfig("../assets/.pybc-imperial.toml")

print(PreferredUnits)
print(get_global_use_powder_sensitivity())
print(get_global_max_calc_step_size())

basicConfig("../assets/.pybc-mixed.toml")

print(PreferredUnits)
print(get_global_use_powder_sensitivity())
print(get_global_max_calc_step_size())