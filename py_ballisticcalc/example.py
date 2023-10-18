"""Example of library usage"""


from py_ballisticcalc import *
from py_ballisticcalc import Settings as Set


# set global library settings
Set.Units.velocity = Velocity.FPS
Set.Units.temperature = Temperature.Celsius
# Set.Units.distance = Distance.Meter
Set.Units.sight_height = Distance.Centimeter

# Set.set_max_calc_step_size(Distance.Foot(1))
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

current_atmo = Atmo(110, 1000, 15, 72)
current_winds = [Wind(2, 90)]
shot = Shot(1500, atmo=current_atmo, winds=current_winds)

shot_result = calc.fire(shot, Distance.Yard(100))

for p in shot_result:
    print(p.formatted())
