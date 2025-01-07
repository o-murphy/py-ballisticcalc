from py_ballisticcalc import Unit
from ukrop_338lm_300gr_smk import calc, shot

from timeit import timeit
number = 120
zero_distance = Unit.Meter(100)
shot_distance = Unit.Meter(1000)

total_time = timeit(lambda: calc.barrel_elevation_for_target(shot, zero_distance), number=number)
rate = number / total_time  # executions per second

print("Calculate barrel elevation at distance {} {} times:".format(zero_distance, number))
print(f"Total time: {total_time:.6f} seconds")
print(f"Execution rate: {rate:.2f} calls per second")

total_time = timeit(lambda: calc.fire(shot, shot_distance, extra_data=False), number=number)
rate = number / total_time  # executions per second

print("Calculate trajectory to distance {} {} times:".format(shot_distance, number))
print(f"Total time: {total_time:.6f} seconds")
print(f"Execution rate: {rate:.2f} calls per second")