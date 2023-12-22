"""Example of library usage"""

from py_ballisticcalc import *
from py_ballisticcalc import Settings as Set

# set global library settings
Set.Units.velocity = Velocity.MPS
Set.Units.adjustment = Unit.CM_PER_100M
Set.Units.temperature = Temperature.Celsius
# Set.Units.distance = Distance.Meter
Set.Units.sight_height = Distance.Centimeter
Set.Units.distance = Distance.Meter

# Set.set_max_calc_step_size(Distance.Foot(1))
Set.USE_POWDER_SENSITIVITY = True  # enable muzzle velocity correction my powder temperature

# define params with default units
weight, diameter = 300, 0.338
# or define with specified units
length = Distance.Inch(1.7)  # length = Distance(1.282, Distance.Inch)

weapon = Weapon(twist=10, zero_distance=Distance.Meter(100),
                sight_height=Unit.CENTIMETER(9))
dm = DragModel(0.381, TableG7, weight, diameter)

ammo = Ammo(
    dm=dm, length=length,
    mv=Unit.MPS(815),
    powder_temp=Unit.CELSIUS(0))

# ammo.calc_powder_sens(
#     other_velocity=Unit.MPS(800),
#     other_temperature=Unit.CELSIUS(-22)
# )
# print(ammo.temp_modifier)
ammo.temp_modifier = 0.0123

# zero_atmo = Atmo.icao(100)
zero_atmo = Atmo(
    altitude=Unit.METER(150),
    pressure=Unit.MM_HG(745),
    temperature=Unit.CELSIUS(-1),
    humidity=78
)

# defining calculator instance
calc = Calculator(weapon, ammo, zero_atmo)

current_atmo = Atmo(
    altitude=Unit.METER(150),
    pressure=Unit.HP(992),
    temperature=Unit.CELSIUS(23),
    humidity=29
)

current_winds = [Wind()]
shot = Shot(Distance.Meter(1000), atmo=current_atmo, winds=current_winds)

shot_result = calc.fire(shot, Distance.Meter(100))

from pprint import pprint
fieldsss = TrajectoryData._fields

for p in shot_result:

    table = [{fieldsss[i]: it} for i, it in enumerate(p.formatted())]

    pprint(table)
