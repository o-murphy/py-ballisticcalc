import pyximport; pyximport.install(language_level=3)
from py_ballisticcalc import *

Settings.Units.velocity = Velocity.MPS

dm = DragModel(0.22, TableG7, 168, 0.308)
ammo = Ammo(dm, 1.22, Velocity(2600, Velocity.FPS))
weapon = Weapon(4, 100, 11.24)

calc = Calculator(weapon, ammo)
calc.calculate_elevation()

shot = Shot(1200, zero_angle=calc.elevation, relative_angle=Angular.Mil(0))
shot_results = calc.fire(shot, Distance.Foot(0.2), TrajFlag.ALL)
trajectory_plot(calc, shot).show()

