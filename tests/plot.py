import matplotlib

from py_ballisticcalc import *
from py_ballisticcalc.visualize.plot import show_hit_result_plot

PreferredUnits.velocity = Velocity.MPS

dm = DragModel(0.22, TableG7, 168, 0.308)
ammo = Ammo(dm, Velocity.FPS(2600))
weapon = Weapon(4, 100, 11.24, Angular.Mil(0))

calc = Calculator()
zero_shot = Shot(ammo, weapon)
calc.set_weapon_zero(zero_shot, Distance.Yard(100))

shot = Shot(ammo, weapon)
shot_result = calc.fire(shot, Distance.Yard(1000), Distance.Yard(10), flags=TrajFlag.ALL)
danger_space = shot_result.danger_space(Distance.Yard(500), Distance.Meter(1.5))
ax = shot_result.plot()
danger_space.overlay(ax)
print(shot_result.dataframe())

matplotlib.use('TkAgg')
show_hit_result_plot()
