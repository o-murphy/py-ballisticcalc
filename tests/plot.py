import pyximport; pyximport.install(language_level=3)
from py_ballisticcalc import *

Settings.Units.velocity = Velocity.MPS

dm = DragModel(0.22, TableG7, 168, 0.308)
ammo = Ammo(dm, 1.22, Velocity(2600, Velocity.FPS))
atmosphere = Atmo.icao()
weapon = Weapon(4, 100, 11.24)

calc = Calculator(weapon, ammo, atmosphere)
calc.update_elevation()
atmo = Atmo.icao()

shot = Shot(1200, Distance.Foot(0.2), zero_angle=calc.elevation, relative_angle=Angular.MOA(0))
calc.show_plot(shot, atmo, [Wind()])
