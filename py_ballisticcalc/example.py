"""Example of library usage"""

from py_ballisticcalc import *
from py_ballisticcalc import Settings as Set

# Modify default units
Set.Units.velocity = Velocity.FPS
Set.Units.temperature = Temperature.Celsius
Set.Units.distance = Distance.Meter
Set.Units.sight_height = Distance.Centimeter

Set.USE_POWDER_SENSITIVITY = True  # enable muzzle velocity correction my powder temperature

# Define ammunition parameters
weight, diameter = 168, 0.308  # Numbers will be assumed to use default Settings.Units
length = Distance.Inch(1.282)  # Or declare units explicitly
dm = DragModel(0.223, TableG7, weight, diameter)
ammo = Ammo(dm, length, 2750, 15)
ammo.calc_powder_sens(2723, 0)

gun = Weapon(sight_height=9, twist=12)
zero_atmo = Atmo.icao(100)

# defining calculator instance
calc = Calculator(weapon=gun, ammo=ammo, zero_atmo=zero_atmo)
calc.set_weapon_zero(Distance.Meter(100))
current_atmo = Atmo(110, 1000, 15, 72)
current_winds = [Wind(2, 90)]
shot = Shot(weapon=gun, atmo=current_atmo, winds=current_winds)

shot_result = calc.fire(shot, trajectory_range=1000, trajectory_step=100)

for p in shot_result:
    print(p.formatted())
