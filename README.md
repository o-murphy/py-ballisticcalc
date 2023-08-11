# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3.9+)
Installation
------------
**Stable release from pypi, installing from binaries**

(Contains c-extensions which offer higher performance)
```commandline
pip install py-ballisticcalc
```

**Build wheel package for your interpreter version by pypi sdist**

Download and install MSVC or GCC depending on target platform
```commandline
pip install Cython>=3.0.0a10 
pip install py-ballisticcalc --no-binary :all:
```

**Also use `git clone` to build your own package**

(Contains cython files to build your own c-extensions)
```commandline
git clone https://github.com/o-murphy/py_ballisticcalc
```   


Usage
-----

### Simple start
```python
from py_ballisticcalc.profile import *
from py_ballisticcalc.bmath import unit


profile = Profile()
tested_data = profile.calculate_trajectory()

for d in tested_data:
    distance = d.travelled_distance().convert(unit.DistanceMeter)
    velocity = d.velocity().convert(unit.VelocityMPS)
    mach = d.mach_velocity()
    energy = d.energy()
    time = round(d.time().total_seconds(), 4)
    path = d.drop().convert(unit.DistanceCentimeter)
    windage = d.windage().convert(unit.DistanceCentimeter)
    print(
        f'Distance: {distance}, '
        f'Velocity: {velocity}, '
        f'Mach: {mach}, '
        f'Energy: {energy}, '
        f'Time: {time}s, '
        f'Path: {path}, '
        f'Windage: {windage}'
    )
```

### Use any modules directly if needed 
```python
from py_ballisticcalc.profile import *
from py_ballisticcalc.projectile import *
from py_ballisticcalc.drag import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.trajectory_calculator import *
from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.wind import *
from py_ballisticcalc.shot_parameters import *
from py_ballisticcalc.bmath import unit

bc = BallisticCoefficient(0.223, DragTableG7, unit.Weight(168, unit.WeightGrain), unit.Distance(0.308, unit.DistanceInch), TableG7)
projectile = ProjectileWithDimensions(bc, unit.Distance(0.308, unit.DistanceInch),
                                      unit.Distance(1.282, unit.DistanceInch),
                                      unit.Weight(168, unit.WeightGrain))
ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS))
zero = ZeroInfo(unit.Distance(100, unit.DistanceMeter))
twist = TwistInfo(TwistRight, unit.Distance(11.24, unit.DistanceInch))
weapon = WeaponWithTwist(unit.Distance(2, unit.DistanceInch), zero, twist)
atmosphere = Atmosphere(unit.Distance(10, unit.DistanceMeter), Pressure(760, PressureMmHg), Temperature(15, TemperatureCelsius), 0.5)
shot_info = ShotParameters(unit.Angular(4.221, unit.AngularMOA),
                           unit.Distance(1001, unit.DistanceMeter),
                           unit.Distance(100, unit.DistanceMeter))
wind = create_only_wind_info(unit.Velocity(5, unit.VelocityMPH),
                                      unit.Angular(-45, unit.AngularDegree))

calc = TrajectoryCalculator()
data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

for d in data:
    distance = d.travelled_distance()
    meters = distance.convert(unit.DistanceMeter)
    velocity = d.velocity().convert(unit.VelocityMPS)
    mach = round(d.mach_velocity(), 4)
    energy = d.energy()
    time = round(d.time().total_seconds(), 4)
    path = d.drop().convert(unit.DistanceCentimeter)
    hold = d.drop_adjustment().get_in(unit.AngularMOA) if distance.get_in(unit.DistanceMeter) > 1 else None
    windage = d.windage().convert(unit.DistanceCentimeter)
    wind_adjustment = d.windage_adjustment().get_in(unit.AngularMOA) if distance.get_in(unit.DistanceMeter) > 1 else None
    print(
        f'Distance: {meters}, '
        f'Velocity: {velocity}, '
        f'Mach: {mach}, '
        f'Energy: {energy}, '
        f'Time: {time}s, '
        f'Path: {path}, '
        f'Windage: {windage}'
    )
```


Info
-----

The library provides trajectory calculation for projectiles including for various
applications, including air rifles, bows, firearms, artillery and so on.

3DF model that is used in this calculator is rooted in old C sources of version 2 of the public version of JBM
calculator, ported to C#, optimized, fixed and extended with elements described in
Litz's "Applied Ballistics" book and from the friendly project of Alexandre Trofimov
and then ported to Go.

Now it's also ported to python3 and expanded to support calculation trajectory by 
multiple ballistics coefficients and using custom drag data (such as Doppler radar data, etc.)

The online version of Go documentation is located here: https://godoc.org/github.com/gehtsoft-usa/go_ballisticcalc

C# version of the package is located here: https://github.com/gehtsoft-usa/BallisticCalculator1

The online version of C# API documentation is located here: https://gehtsoft-usa.github.io/BallisticCalculator/web-content.html

Go documentation can be obtained using godoc tool.