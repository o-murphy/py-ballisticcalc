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
from timeit import timeit
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger
import logging

from py_ballisticcalc.interface import _EngineLoader

logger.setLevel(logging.INFO)

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
shot_distance: Distance = Unit.Meter(1000)

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
    calc_.fire(shot, shot_distance, flags=TrajFlag.ALL)
    return shot


def run_check(calc_: Calculator, number: int):
    total_time = timeit(lambda: calc_.barrel_elevation_for_target(init_zero_shot(), zero_distance), number=number)
    rate = number / total_time  # executions per second

    print("Calculate barrel elevation at distance {} {} times:".format(zero_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")

    # preinit
    zero_shot = init_zero_shot()
    calc_.set_weapon_zero(zero_shot, zero_distance)
    shot = Shot(weapon=zero_shot.weapon, ammo=zero_shot.ammo, atmo=current_atmo)

    total_time = timeit(lambda: calc_.fire(shot, shot_distance), number=number)
    rate = number / total_time  # executions per second

    print("Calculate trajectory to distance {} {} times:".format(shot_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")

    total_time = timeit(lambda: calc_.fire(shot, shot_distance, flags=TrajFlag.ALL), number=number)
    rate = number / total_time  # executions per second

    print("Calculate trajectory to distance + extra {} {} times:".format(shot_distance, number))
    print(f"Total time: {total_time:.6f} seconds")
    print(f"Execution rate: {rate:.2f} calls per second")

    if calc_._engine_factory.__name__.lower().startswith("cythonized"):
        key_attribute = 'position.x'
        target_value = shot_distance._feet

        total_time = timeit(lambda: calc_.integrate_raw_at(shot, key_attribute, target_value), number=number)
        rate = number / total_time  # executions per second

        print(f"Calculate integrate_raw_at({key_attribute=}, {target_value=}) {shot_distance} {number} times:")
        print(f"Total time: {total_time:.6f} seconds")
        print(f"Execution rate: {rate:.2f} calls per second")

    print()


def check_all(number = 120):
    [print(f"Detected: {e}") for e in _EngineLoader.iter_engines()]
    print()

    for ep in _EngineLoader.iter_engines():
        config = {}

        if ep.name in {"verlet_engine"}:
        # if ep.name in {"euler_engine", "rk4_engine"}:
            continue  # skip pure ones
        elif ep.name in {"cythonized_euler_engine", "cythonized_rk4_engine"}:
            ...
        # elif ep.name in {"scipy"}:
        #     config: SciPyEngineConfigDict = {
        #         "relative_tolerance": 1e-6,
        #         "absolute_tolerance": 1e-5,
        #     }

        engine = ep.load()
        print("Engine: %s" % ep.value)
        # if ep.name.startswith("scipy"):
        #     config: SciPyEngineConfigDict = {
        #         "relative_tolerance": 1e-4,
        #         "absolute_tolerance": 1e-3,
        #         "integration_method": "LSODA"
        #     }
        calc = Calculator(config=config, engine=engine)
        run_check(calc, number)
        print()


engines = {
    "euler": "euler_engine", 
    "rk4": "euler_engine", 
    "verlet": "verlet_engine", 
    "cythonized_euler": "cythonized_euler_engine", 
    "cythonized_rk4": "cythonized_rk4_engine",
    "scipy": "scipy_engine",
    "all": "all", 
}


def check_one(en, m, number = 120):
    config = {}
    if en == "scipy":
        config["integration_method"] = m

    calc = Calculator(config=config, engine=en)
    run_check(calc, number)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e",
        help="engine", 
        choices=[
            "euler", 
            "rk4", 
            "verlet", 
            "cythonized_euler", 
            "cythonized_rk4",
            "scipy",
            "all", 
        ], 
        default="rk4"
    )
    parser.add_argument("-m", help="SciPy method", choices=["RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"], default="RK45")
    parser.add_argument("-n", help="number", type=int, default=120)

    args = parser.parse_args()
    print(args)

    if args.e == "all":
        check_all()
    else:
        en = engines.get(args.e)
        if not en:
            parser.error("Unknown engine")
        check_one(en, args.m, args.n)

if __name__ == "__main__":
    main()

# Engine: py_ballisticcalc_exts:CythonizedEulerIntegrationEngine
# Calculate barrel elevation at distance 100.0m 120 times:
# Total time: 0.066933 seconds
# Execution rate: 1792.83 calls per second
# Calculate trajectory to distance 1000.0m 120 times:
# Total time: 0.227643 seconds
# Execution rate: 527.14 calls per second
# Calculate trajectory to distance + extra 1000.0m 120 times:
# Total time: 0.227960 seconds
# Execution rate: 526.41 calls per second
#
#
# Engine: py_ballisticcalc_exts:CythonizedRK4IntegrationEngine
# Calculate barrel elevation at distance 100.0m 120 times:
# Total time: 0.060389 seconds
# Execution rate: 1987.11 calls per second
# Calculate trajectory to distance 1000.0m 120 times:
# Total time: 0.180230 seconds
# Execution rate: 665.82 calls per second
# Calculate trajectory to distance + extra 1000.0m 120 times:
# Total time: 0.179801 seconds
# Execution rate: 667.40 calls per second


# Engine: py_ballisticcalc_exts:CythonizedEulerIntegrationEngine
# Calculate barrel elevation at distance 100.0m 120 times:
# Total time: 0.042595 seconds
# Execution rate: 2817.23 calls per second
# Calculate trajectory to distance 1000.0m 120 times:
# Total time: 0.147596 seconds
# Execution rate: 813.03 calls per second
# Calculate trajectory to distance + extra 1000.0m 120 times:
# Total time: 0.151805 seconds
# Execution rate: 790.49 calls per second
#
#
# Engine: py_ballisticcalc_exts:CythonizedRK4IntegrationEngine
# Calculate barrel elevation at distance 100.0m 120 times:
# Total time: 0.037839 seconds
# Execution rate: 3171.34 calls per second
# Calculate trajectory to distance 1000.0m 120 times:
# Total time: 0.117954 seconds
# Execution rate: 1017.34 calls per second
# Calculate trajectory to distance + extra 1000.0m 120 times:
# Total time: 0.119256 seconds
# Execution rate: 1006.24 calls per second