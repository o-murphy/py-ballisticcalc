"""
Example of library usage
"""
import pyximport

pyximport.install(language_level=3)

from py_ballisticcalc.environment import *
from py_ballisticcalc.projectile import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.unit import *
from py_ballisticcalc.shot import ShotParameters
from py_ballisticcalc.trajectory_calculator import TrajectoryCalculator
from py_ballisticcalc.drag import DragModel
from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.trajectory_data import TrajectoryData

# defining calculator instance
calc = TrajectoryCalculator()
# calc.set_maximum_calculator_step_size(maximum_step_size)  # optional

# bullet
bullet_weight = Weight(0.250, Weight.Grain)
bullet_diameter = Distance(0.308, Distance.Inch)
bullet_length = Distance(1.555, Distance.Inch)
dm = DragModel(0.314, TableG7, bullet_weight, bullet_diameter)

# ammo
muzzle_velocity = Velocity(800, Velocity.MPS)

# weapon and ammo
sight_height = Distance(90, Distance.Millimeter)
twist = Distance(9, Distance.Inch)

# conditions
winds = [Wind()]
zero_atmo = Atmosphere.ICAO()

# summary
projectile = Projectile(dm, bullet_weight, bullet_diameter, bullet_length)
weapon = Weapon(sight_height, twist=twist)
ammo = Ammo(projectile, muzzle_velocity)

# shot parameters
sight_angle = calc.sight_angle(ammo, weapon, zero_atmo)
max_range = Distance(2000, Distance.Meter)
calc_step = Distance(50, Distance.Meter)
shot_atmo = Atmosphere(
    altitude=Distance(100, Distance.Meter),
    temperature=Temperature(20, Temperature.Celsius),
    pressure=Pressure(760, Pressure.MmHg),
    humidity=50
)
shot = ShotParameters(sight_angle, max_range, calc_step)

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
            fmt(p.distance, Distance.Meter),
            fmt(p.velocity, Velocity.MPS),
            f'{p.mach:.2f} mach',
            fmt(p.drop, Distance.Centimeter),
            fmt(p.drop_adj, Angular.Mil),
            fmt(p.windage, Distance.Centimeter),
            fmt(p.windage_adj, Angular.Mil),
            fmt(p.energy, Energy.Joule)
        ]
    )
