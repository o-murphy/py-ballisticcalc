"""Example of library usage"""

# pylint: disable=wildcard-import,unused-wildcard-import
from py_ballisticcalc import *


# Modify default prefer_units
PreferredUnits.velocity = Velocity.FPS
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter

# Define ammunition parameters
weight, diameter = 168, 0.308  # Numbers will be assumed to use default Settings.Units
length: Distance = Distance.Inch(1.282)  # Or declare prefer_units explicitly
dm = DragModel(0.223, TableG7, weight, diameter, length)
ammo = Ammo(dm, 2750, 15, use_powder_sensitivity=True)
ammo.calc_powder_sens(2723, 0)
gun = Weapon(sight_height=9, twist=12)
current_atmo = Atmo(110, 29.8, 15, 72)
current_winds = [Wind(2, 90)]
shot = Shot(weapon=gun, ammo=ammo, atmo=current_atmo, winds=current_winds)
calc = Calculator()
calc.set_weapon_zero(shot, Distance.Meter(100))

shot_result = calc.fire(shot, trajectory_range=1000, trajectory_step=100)

for p in shot_result:
    print(p.formatted())
