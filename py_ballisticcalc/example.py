"""
Example of library usage
"""
import pyximport

pyximport.install(language_level=3)

from py_ballisticcalc.conditions import *
from py_ballisticcalc.projectile import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.unit import *
from py_ballisticcalc.trajectory_calc import TrajectoryCalc
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.trajectory_data import TrajectoryData


# defining calculator instance
calc = TrajectoryCalc()

# bullet
weight = 175
diameter = 0.308
dm = DragModel(0.275, TableG7, weight, diameter)

zero_atmo = Atmo.ICAO(100)

# summary
projectile = Projectile(dm, weight, diameter, 1.2)
weapon = Weapon(2, 100, 9)
ammo = Ammo(projectile, 800)
winds = [Wind(5, -45)]  # wind from 3 o'clock

# shot parameters
zero_sight_angle = calc.sight_angle(ammo, weapon, zero_atmo)
shot_atmo = Atmo(100, 1000, 20, 50)
shot = Shot(zero_sight_angle, 2000, 50)


data = calc.trajectory(ammo, weapon, shot_atmo, shot, winds)

header = list(TrajectoryData._fields)


def fmt(v: AbstractUnit, u: Unit):
    return f"{v >> u:.{u.accuracy}f} {u.symbol}"
    # return "{:.{}f} {}".format(v >> u, u.accuracy, u.symbol)
    # return "{v:.{a}f} {s}".format(v=v >> u, a=u.accuracy, s=u.symbol)


for p in data:
    print(
        [
            f'{p.time:.2f} s',
            fmt(p.distance, DefaultUnits.distance),
            fmt(p.velocity, DefaultUnits.velocity),
            f'{p.mach:.2f} mach',
            fmt(p.drop, DefaultUnits.drop),
            fmt(p.drop_adj, DefaultUnits.adjustment),
            fmt(p.windage, DefaultUnits.drop),
            fmt(p.windage_adj, DefaultUnits.adjustment),
            fmt(p.energy, DefaultUnits.energy)
        ]
    )

# for p in data:
#     print(
#         [
#             f'{p.time:.2f} s',
#             fmt(p.distance, Distance.Meter),
#             fmt(p.velocity, Velocity.MPS),
#             f'{p.mach:.2f} mach',
#             fmt(p.drop, Distance.Centimeter),
#             fmt(p.drop_adj, Angular.Mil),
#             fmt(p.windage, Distance.Centimeter),
#             fmt(p.windage_adj, Angular.Mil),
#             fmt(p.energy, Energy.Joule)
#         ]
#     )
