"""
cythonized extensions should improve performance

Last results:

Got:
    up to 10 times faster with extra_data=False with cython
    up to 2 times faster with extra_data=True with cython


pure python:

    Calculate barrel elevation at distance 100.0m 120 times:
    Total time: 1.638778 seconds
    Execution rate: 73.23 calls per second

    extra_data=False:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 9.233984 seconds
        Execution rate: 13.00 calls per second

    extra_data=True:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 24.767394 seconds
        Execution rate: 4.85 calls per second

cythonized:

    Calculate barrel elevation at distance 100.0m 120 times:
    Total time: 0.284459 seconds
    Execution rate: 421.85 calls per second

    extra_data=False:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 0.969684 seconds
        Execution rate: 123.75 calls per second

    extra_data=True:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 11.529288 seconds
        Execution rate: 10.41 calls per second
"""

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

total_time = timeit(lambda: calc.fire(shot, shot_distance, extra_data=True), number=number)
rate = number / total_time  # executions per second

print("Calculate trajectory to distance {} {} times:".format(shot_distance, number))
print(f"Total time: {total_time:.6f} seconds")
print(f"Execution rate: {rate:.2f} calls per second")
