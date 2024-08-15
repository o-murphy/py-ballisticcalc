"""Example of library usage"""
import math

from py_ballisticcalc import *


# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter


# set_global_use_powder_sensitivity(True)  # enable muzzle velocity correction my powder temperature

# define params with default prefer_units
length = Distance.Inch(2.3)

weapon = Weapon(sight_height=Unit.Centimeter(9.5), twist=15)
dm = DragModel(0.62, TableG1, 661, 0.51)
ammo = Ammo(dm, 900)

zero_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.hPa(1000),
    temperature=Unit.Celsius(15),
    humidity=50
)
zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
zero_distance = Distance.Meter(500)

calc = Calculator()
calc.set_weapon_zero(zero, zero_distance)

shot = Shot(look_angle=Unit.Degree(20), weapon=weapon, ammo=ammo, atmo=zero_atmo)
shot_result = calc.fire(shot, Distance.Meter(1000), Distance.Meter(100))

from pprint import pprint
fieldsss = TrajectoryData._fields

# for p in shot_result:
#
#     # table = [{fieldsss[i]: it} for i, it in enumerate(p.in_def_units())]
#     #
#     # pprint(table)
#     print(p.in_def_units(),  ",")


def calculate_lead_angle(target_speed, target_size, bullet_speed, initial_distance, time_of_flight):
    """
    Розрахунок кута упередження маючи швидкість і розмір цілі, швидкість кулі, початкову відстань до цілі.

    :param target_speed: Швидкість цілі (м/с)
    :param target_size: Довжина цілі (м)
    :param bullet_speed: Швидкість кулі (м/с)
    :param initial_distance: Початкова відстань до цілі (м)
    :return: Кут упередження в градусах
    """
    # Час польоту кулі
    # time_of_flight = initial_distance / bullet_speed

    # Відстань, яку пройде ніс цілі
    # distance_nose_travel = target_speed * time_of_flight + target_size
    distance_nose_travel = target_speed * time_of_flight + target_size

    # Обчислення кута упередження
    lead_angle = math.atan(distance_nose_travel / initial_distance)

    # Перетворення кута в градуси
    lead_angle_degrees = math.degrees(lead_angle)

    return lead_angle_degrees

target_speed = 50
target_size = 3
max_lead_angle = 6.21


for p in shot_result:

    table = [{fieldsss[i]: it} for i, it in enumerate(p.formatted())]

    pprint(table)

# for p in shot_result[1:]:
#     values = p.in_def_units()
#     a = calculate_lead_angle(target_speed, target_size, values[2], values[1], values[0])
#     # if a > max_lead_angle:
#     #     continue
#     print(f"{a:.2f}°, {values[1]:.0f}m, {values[2]:.0f}m/s")
