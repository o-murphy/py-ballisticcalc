"""
Example of library usage
"""
import pyximport
pyximport.install(language_level=3)

from py_ballisticcalc.interface import *


# set global library settings
DefaultUnits.velocity = Velocity.MPS
DefaultUnits.distance = Distance.Meter
MIN_CALC_STEP_SIZE = Distance(2, Distance.Meter)


# define params with default units
weight, diameter = 175, 0.308
# or define with specified units
length = Distance(1.2, Distance.Inch)


weapon = Weapon(90, 100, 9)
dm = DragModel(0.275, TableG7, weight, diameter)
bullet = Projectile(dm, length)
ammo = Ammo(bullet, 800)

c = ammo._calc_powder_sens(792, 0)
print(c)
print(ammo._get_velocity_for_temp(15))
print(ammo._get_velocity_for_temp(0))

zero_atmo = Atmo.ICAO()

# defining calculator instance
calc = Calculator(weapon, ammo, zero_atmo)
calc.update_elevation()

shot = Shot(1500, 100)
current_atmo = Atmo(100, 1000, 20, 72)
winds = [Wind(2, 90)]

data = calc.trajectory(shot, current_atmo, winds)

for p in data:
    print(p.formatted())

"""
Example of the formatted output:

['0.00 s', '0.000 m', '800 m/s', '2.33 mach', '-90.000 cm', '0.00 mil', '0.000 cm', '0.00 mil', '3629 J']
['0.13 s', '100.000 m', '747 m/s', '2.18 mach', '0.009 cm', '0.00 mil', '0.527 cm', '0.05 mil', '3165 J']
['0.27 s', '200.050 m', '696 m/s', '2.03 mach', '72.444 cm', '3.69 mil', '2.300 cm', '0.12 mil', '2749 J']
['0.42 s', '300.050 m', '647 m/s', '1.89 mach', '124.565 cm', '4.23 mil', '5.466 cm', '0.19 mil', '2377 J']
['0.58 s', '400.000 m', '601 m/s', '1.75 mach', '153.234 cm', '3.90 mil', '10.150 cm', '0.26 mil', '2047 J']
['0.75 s', '500.000 m', '556 m/s', '1.62 mach', '154.685 cm', '3.15 mil', '16.493 cm', '0.34 mil', '1751 J']
['0.94 s', '600.000 m', '512 m/s', '1.49 mach', '124.303 cm', '2.11 mil', '24.651 cm', '0.42 mil', '1489 J']
['1.14 s', '700.000 m', '470 m/s', '1.37 mach', '56.452 cm', '0.82 mil', '34.803 cm', '0.51 mil', '1255 J']
['1.36 s', '800.000 m', '430 m/s', '1.25 mach', '-55.854 cm', '-0.71 mil', '47.152 cm', '0.60 mil', '1049 J']
['1.61 s', '900.000 m', '392 m/s', '1.14 mach', '-221.359 cm', '-2.51 mil', '61.906 cm', '0.70 mil', '870 J']
['1.88 s', '1000.000 m', '355 m/s', '1.04 mach', '-451.055 cm', '-4.59 mil', '79.257 cm', '0.81 mil', '717 J']
['2.17 s', '1100.000 m', '328 m/s', '0.96 mach', '-758.514 cm', '-7.02 mil', '99.103 cm', '0.92 mil', '610 J']
['2.48 s', '1200.000 m', '314 m/s', '0.92 mach', '-1156.741 cm', '-9.82 mil', '119.842 cm', '1.02 mil', '560 J']
['2.81 s', '1300.000 m', '304 m/s', '0.88 mach', '-1654.421 cm', '-12.96 mil', '140.416 cm', '1.10 mil', '522 J']
['3.14 s', '1400.000 m', '294 m/s', '0.86 mach', '-2258.848 cm', '-16.43 mil', '160.496 cm', '1.17 mil', '491 J']
['3.49 s', '1500.000 m', '285 m/s', '0.83 mach', '-2977.146 cm', '-20.21 mil', '179.875 cm', '1.22 mil', '462 J']
"""
