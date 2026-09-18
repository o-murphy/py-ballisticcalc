"""Example of library usage"""
# import RKballistic
import os
from concurrent.futures import ThreadPoolExecutor
from copy import copy
import logging
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger

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

weapon = Weapon(sight_height=Unit.Centimeter(9), twist=10)
dm = DragModel(0.381, TableG7, weight, diameter, length)
ammo = Ammo(dm=dm, mv=Unit.MPS(815), powder_temp=Temperature.Celsius(0), temp_modifier=0.0123,
            use_powder_sensitivity=True)

zero_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.MmHg(745),
    temperature=Unit.Celsius(-1),
    humidity=78
)
zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
zero_distance = Distance.Meter(100)

config: BaseEngineConfigDict = {}
calc = Calculator(config=config, engine="cythonized_dopri_engine")
calc.set_weapon_zero(zero, zero_distance)

current_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.hPa(992),
    temperature=Unit.Celsius(23),
    humidity=29,
)
shot = Shot(weapon=weapon, ammo=ammo, atmo=current_atmo)

distances = [Distance.Meter(d) for d in range(100, 3001, 1)]

def make_aim_table():
    data = []
    for d in distances:
        hold, windage, _point = calc.aim(shot, d)
        data.append((d, hold >> Angular.Mil, windage >> Angular.Mil))

from time import perf_counter
from datetime import timedelta

start = perf_counter()
make_aim_table()
end = perf_counter()

print("Seq time:", timedelta(seconds=end - start))


# 1. Визначаємо кількість доступних ядер CPU
NUM_WORKERS = os.cpu_count() or 1

# 2. Клонуємо калькулятори під кожне ядро (щоб у кожного потоку був свій C++ інстанс)
# Якщо у вас реалізовано метод calc.clone(), краще використати його
calc_pool = [copy(calc) for _ in range(NUM_WORKERS)]

def make_aim_table_parallel():
    # Розкидаємо дистанції між воркерами (Interleaved / Round-Robin)
    # Це гарантує ідеальне балансування навантаження (Load Balancing)
    tasks_per_worker = [[] for _ in range(NUM_WORKERS)]
    for idx, d in enumerate(distances):
        tasks_per_worker[idx % NUM_WORKERS].append(d)

    # Воркер, який виконує свій шматок дистанцій на своєму C++ інстансі
    def worker_task(worker_id):
        local_calc = calc_pool[worker_id]
        local_distances = tasks_per_worker[worker_id]
        local_data = []
        
        for d in local_distances:
            hold, windage, _point = local_calc.aim(shot, d)
            local_data.append((d, hold >> Angular.Mil, windage >> Angular.Mil))
            
        return local_data

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(worker_task, w_id) for w_id in range(NUM_WORKERS)]
        
        data = []
        for f in futures:
            data.extend(f.result())

    return data


start = perf_counter()
results = make_aim_table_parallel()
end = perf_counter()

print("Parallel time:", timedelta(seconds=end - start))