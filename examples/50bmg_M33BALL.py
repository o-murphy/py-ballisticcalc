"""Example of library usage"""
# import RKballistic

import logging
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger
from matplotlib import pyplot as plt

logger.setLevel(logging.DEBUG)

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Mil
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter


class Setup:
    weight = Unit.Grain(661.0)
    diameter = Unit.Inch(0.51)
    length = Unit.Inch(2.31)
    bc = 0.62
    model = TableG1
    sh = Unit.Centimeter(15.0)
    psens = 0.014
    ptemp = Unit.Celsius(15.0)
    mv = Unit.MPS(837.0)
    zero = Unit.Meter(100.0)
    twist = Unit.Inch(10.0)
    target = Unit.Meter(1000.0)


weapon = Weapon(sight_height=Setup.sh, twist=Setup.twist)
ammo = Ammo(
    dm=DragModel(Setup.bc, Setup.model, Setup.weight, Setup.diameter, Setup.length),
    mv=Setup.mv,
    powder_temp=Setup.ptemp,
    temp_modifier=Setup.psens,
    use_powder_sensitivity=True,
)

atmo = Atmo.icao()

zero = Shot(weapon=weapon, ammo=ammo, atmo=atmo)

calc = Calculator(engine="cythonized_rk4_engine")
calc.set_weapon_zero(zero, Setup.zero)

shot = Shot(weapon=weapon, ammo=ammo, atmo=atmo)

shot_result = calc.fire(shot, Setup.target, trajectory_step=Unit.Meter(10.0))
shot_result.plot()
plt.show()
