import pyximport; pyximport.install(language_level=3)
from py_ballisticcalc import *
import matplotlib
from matplotlib import pyplot as plt

matplotlib.use('TkAgg')

Settings.Units.velocity = Velocity.MPS

dm = DragModel(0.22, TableG7, 168, 0.308)
ammo = Ammo(dm, 1.22, Velocity(2600, Velocity.FPS))
weapon = Weapon(4, 100, 11.24)

calc = Calculator(weapon, ammo)
calc.calculate_elevation()

shot = Shot(1200, zero_angle=calc.elevation, relative_angle=Angular.Mil(0))
shot_result = calc.fire(shot, 0, extra_data=True)
danger_space = shot_result.danger_space(
    Distance.Yard(500), Distance.Meter(1.5), 0
)
ax = shot_result.plot()
danger_space.overlay(ax)
plt.show()
