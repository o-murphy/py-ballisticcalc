"""Example of library usage"""

import logging

try:
    import pyximport
    pyximport.install(language_level=3)
except ImportError as err:
    pyximport = None
    logging.error(err)
    logging.warning("Install Cython to use pyximport")


from py_ballisticcalc import Velocity, Temperature, Distance
from py_ballisticcalc import DragModel, TableG7
from py_ballisticcalc import Ammo, Atmo, Wind
from py_ballisticcalc import Weapon, Shot, Calculator
from py_ballisticcalc import Settings as Set


# set global library settings
Set.Units.velocity = Velocity.FPS
Set.Units.temperature = Temperature.Celsius
# Set.Units.distance = Distance.Meter
Set.Units.sight_height = Distance.Centimeter

Set.set_max_calc_step_size(Distance.Foot(1))
Set.USE_POWDER_SENSITIVITY = True  # enable muzzle velocity correction my powder temperature

# define params with default units
weight, diameter = 168, 0.308
# or define with specified units
length = Distance.Inch(1.282)  # length = Distance(1.282, Distance.Inch)

weapon = Weapon(9, 100, 2)
dm = DragModel(0.223, TableG7, weight, diameter)

ammo = Ammo(dm, length, 2750, 15)
ammo.calc_powder_sens(2723, 0)

zero_atmo = Atmo.icao(100)

# defining calculator instance
calc = Calculator(weapon, ammo, zero_atmo)
calc.update_elevation()

shot = Shot(1500, 100)
print(shot.max_range)
print(zero_atmo.temperature)

current_atmo = Atmo(110, 1000, 15, 72)
winds = [Wind(2, 90)]
print(weapon.sight_height)

data = calc.trajectory(shot, current_atmo, winds)

for p in data:
    print(p.formatted())
