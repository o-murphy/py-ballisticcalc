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
import RKballistic
from timeit import timeit
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger
import logging

logger.setLevel(logging.DEBUG)

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter

# define params with default prefer_units
weight, diameter = 300, 0.338
# or define with specified prefer_units
length = Distance.Inch(1.7)

zero_distance = Distance.Meter(100)
shot_distance = Unit.Meter(1000)

current_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.hPa(992),
    temperature=Unit.Celsius(23),
    humidity=29,
)

zero_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.MmHg(745),
    temperature=Unit.Celsius(-1),
    humidity=78
)

def init_zero_shot():

    weapon = Weapon(sight_height=Unit.Centimeter(9), twist=10)
    dm = DragModel(0.381, TableG7, weight, diameter, length)
    ammo = Ammo(dm=dm, mv=Unit.MPS(815), powder_temp=Temperature.Celsius(0), temp_modifier=0.0123,
                use_powder_sensitivity=True)

    zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)


    return zero

def use_zero_shot(calc_):
    zero = init_zero_shot()
    calc_.set_weapon_zero(zero, zero_distance)

    shot = Shot(weapon=zero.weapon, ammo=zero.ammo, atmo=current_atmo)
    calc_.fire(shot, shot_distance, extra_data=True)
    return shot


config: InterfaceConfigDict = {}
calc = Calculator(_config=config)
rk4 = RKballistic.RK4Calculator(_config=config)




logger.debug("Euler iter")
use_zero_shot(calc)
logger.debug("RK4 iter")
use_zero_shot(rk4)
print(type(rk4), type(rk4._calc))

number = 120


def run_check(calc_):
    total_time = timeit(lambda: calc_.barrel_elevation_for_target(init_zero_shot(), zero_distance), number=number)
    rate = number / total_time  # executions per second

    print("Calculate barrel elevation at distance {} {} times:".format(zero_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")

    # preinit
    zero_shot = init_zero_shot()
    calc_.set_weapon_zero(zero_shot, zero_distance)
    shot = Shot(weapon=zero_shot.weapon, ammo=zero_shot.ammo, atmo=current_atmo)


    total_time = timeit(lambda: calc_.fire(shot, shot_distance, extra_data=False), number=number)
    rate = number / total_time  # executions per second

    print("Calculate trajectory to distance {} {} times:".format(shot_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")

    total_time = timeit(lambda: calc_.fire(shot, shot_distance, extra_data=True), number=number)
    rate = number / total_time  # executions per second

    print("Calculate trajectory to distance + extra {} {} times:".format(shot_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")
    print()


logger.setLevel(logging.INFO)


logger.debug("Euler bench")
run_check(calc)
logger.debug("RK4 bench")
run_check(rk4)
