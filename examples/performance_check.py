"""
cythonized extensions should improve performance

Last results:

Got:
    up to 10 times faster with extra_data=False with cython
    up to 2 times faster with extra_data=True with cython


pure python:

    Calculate barrel elevation at distance 100.0m 120 times:
    Total time: 2.296317 seconds
    Execution rate: 52.26 calls per second

    extra_data=False:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 8.731324 seconds
        Execution rate: 13.74 calls per second

    extra_data=True:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 23.651555 seconds
        Execution rate: 5.07 calls per second

cythonized:

    Calculate barrel elevation at distance 100.0m 120 times:
    Total time: 0.273300 seconds
    Execution rate: 439.08 calls per second

    extra_data=False:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 1.010342 seconds
        Execution rate: 118.77 calls per second

    extra_data=True:

        Calculate trajectory to distance 1000.0m 120 times:
        Total time: 11.458543 seconds
        Execution rate: 10.47 calls per second
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
