"""Example of library usage"""
from py_ballisticcalc import *


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
ammo = Ammo(dm=dm, mv=Unit.MPS(815), powder_temp=Temperature.Celsius(0), temp_modifier=0.0123, use_powder_sensitivity=True)

zero_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.MmHg(745),
    temperature=Unit.Celsius(-1),
    humidity=78
)
zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
zero_distance=Distance.Meter(100)

config: InterfaceConfigDict = {}
calc = Calculator(_config=config)
calc.set_weapon_zero(zero, zero_distance)

current_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.hPa(992),
    temperature=Unit.Celsius(23),
    humidity=29,
)
shot = Shot(weapon=weapon, ammo=ammo, atmo=current_atmo)
shot_result = calc.fire(shot, Distance.Meter(1000), extra_data=False)
print(shot_result.trajectory[0].velocity << Unit.MPS)
#
#
# from pprint import pprint
# fieldsss = TrajectoryData._fields
#
# for p in shot_result:
#
#     table = [{fieldsss[i]: it} for i, it in enumerate(p.formatted())]
#
#     pprint(table)