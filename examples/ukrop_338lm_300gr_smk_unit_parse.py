"""Example of library usage"""

from py_ballisticcalc import *
from py_ballisticcalc.unit import _parse_value, _parse_unit

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter

# define params with default prefer_units
weight = _parse_value('300gr', 'weight')  # using specified alias
diameter = _parse_value(0.338, 'in')  # using preferred alias of type(str)
# or define with specified prefer_units
length = _parse_value('1.7', Unit.Inch)  # using preferred alias of type(Unit)

# by preferred alias by PreferredUnits modifier and numeric value
weapon = Weapon(sight_height=_parse_value(9, "sight_height"),
                twist=_parse_value(9, _parse_unit("twist")))

# no changes bellow
dm = DragModel(0.381, TableG7, weight, diameter, length)
ammo = Ammo(dm=dm, mv=Unit.MPS(815), powder_temp=Temperature.Celsius(0),
            temp_modifier=0.0123, use_powder_sensitivity=True)

zero_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.MmHg(745),
    temperature=Unit.Celsius(-1),
    humidity=78
)
zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
zero_distance=Distance.Meter(100)

calc = Calculator()
calc.set_weapon_zero(zero, zero_distance)

current_atmo = Atmo(
    altitude=Unit.Meter(150),
    pressure=Unit.hPa(992),
    temperature=Unit.Celsius(23),
    humidity=29
)
shot = Shot(weapon=weapon, ammo=ammo, atmo=current_atmo)
shot_result = calc.fire(shot, Distance.Meter(1000))

from pprint import pprint
fieldsss = TrajectoryData._fields

for p in shot_result:

    table = [{fieldsss[i]: it} for i, it in enumerate(p.formatted())]

    pprint(table)
