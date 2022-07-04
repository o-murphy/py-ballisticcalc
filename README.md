# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3)

Installation
------------
    # stable release from pypi
    pip install py-ballisticcalc

    # latest release, may contain some issues
    pip install git+https://github.com/o-murphy/py_ballisticcalc

Usage
-----

### Simple start
```python
from py_ballisticcalc.profile import Profile
from py_ballisticcalc.bmath import unit


profile = Profile()
tested_data = profile.trajectory_data

for d in tested_data:
    distance = d.travelled_distance.convert(unit.DistanceMeter)
    velocity = d.velocity.convert(unit.VelocityMPS)
    mach = round(d.mach_velocity, 4)
    energy = d.energy
    time = round(d.time.total_seconds, 4)
    ogv = d.optimal_game_weight.get_in(unit.WeightPound)
    path = d.drop.convert(unit.DistanceCentimeter)
    hold = d.drop_adjustment.get_in(unit.AngularMOA) if distance.v > 1 else None
    windage = d.windage.convert(unit.DistanceCentimeter)
    wind_adjustment = d.windage_adjustment.get_in(unit.AngularMOA) if distance.v > 1 else None
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

### Extended
#### Using with custom drag table
```python
from py_ballisticcalc.extended import ProfileExtended

custom_drag_func = [
    {'A': 0.0, 'B': 0.18}, {'A': 0.4, 'B': 0.178}, {'A': 0.5, 'B': 0.154},
    {'A': 0.6, 'B': 0.129}, {'A': 0.7, 'B': 0.131}, {'A': 0.8, 'B': 0.136},
    {'A': 0.825, 'B': 0.14}, {'A': 0.85, 'B': 0.144}, {'A': 0.875, 'B': 0.153},
    {'A': 0.9, 'B': 0.177}, {'A': 0.925, 'B': 0.226}, {'A': 0.95, 'B': 0.26},
    {'A': 0.975, 'B': 0.349}, {'A': 1.0, 'B': 0.427}, {'A': 1.025, 'B': 0.45},
    {'A': 1.05, 'B': 0.452}, {'A': 1.075, 'B': 0.45}, {'A': 1.1, 'B': 0.447},
    {'A': 1.15, 'B': 0.437}, {'A': 1.2, 'B': 0.429}, {'A': 1.3, 'B': 0.418},
    {'A': 1.4, 'B': 0.406}, {'A': 1.5, 'B': 0.394}, {'A': 1.6, 'B': 0.382},
    {'A': 1.8, 'B': 0.359}, {'A': 2.0, 'B': 0.339}, {'A': 2.2, 'B': 0.321},
    {'A': 2.4, 'B': 0.301}, {'A': 2.6, 'B': 0.28}, {'A': 3.0, 'B': 0.25},
    {'A': 4.0, 'B': 0.2}, {'A': 5.0, 'B': 0.18}
]

profile = ProfileExtended(drag_table=0, custom_drag_function=custom_drag_func)
custom_drag_func_trajectory = profile.trajectory_data
```

### Use any modules directly if needed 
```python
from py_ballisticcalc.projectile import *
from py_ballisticcalc.drag import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.trajectory_calculator import *
from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.shot_parameters import *
from py_ballisticcalc.bmath import unit

bc = BallisticCoefficient(0.223, DragTableG7)
projectile = ProjectileWithDimensions(bc, unit.Distance(0.308, unit.DistanceInch).validate(),
                                      unit.Distance(1.282, unit.DistanceInch).validate(),
                                      unit.Weight(168, unit.WeightGrain).validate())
ammo = Ammunition(projectile, unit.Velocity(2750, unit.VelocityFPS).validate())
zero = ZeroInfo(unit.Distance(100, unit.DistanceMeter).validate())
twist = TwistInfo(TwistRight, unit.Distance(11.24, unit.DistanceInch).validate())
weapon = Weapon.create_with_twist(unit.Distance(2, unit.DistanceInch).validate(), zero, twist)
atmosphere = Atmosphere()
shot_info = ShotParameters(unit.Angular(4.221, unit.AngularMOA).validate(),
                           unit.Distance(1001, unit.DistanceMeter).validate(),
                           unit.Distance(100, unit.DistanceMeter).validate())
wind = WindInfo.create_only_wind_info(unit.Velocity(5, unit.VelocityMPH).validate(),
                                      unit.Angular(-45, unit.AngularDegree).validate())

calc = TrajectoryCalculator()
data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)

for d in data:
    distance = d.travelled_distance
    meters = distance.convert(unit.DistanceMeter)
    velocity = d.velocity.convert(unit.VelocityMPS)
    mach = round(d.mach_velocity, 4)
    energy = d.energy
    time = round(d.time.total_seconds, 4)
    ogv = d.optimal_game_weight.get_in(unit.WeightPound)
    path = d.drop.convert(unit.DistanceCentimeter)
    hold = d.drop_adjustment.get_in(unit.AngularMOA) if distance.v > 1 else None
    windage = d.windage.convert(unit.DistanceCentimeter)
    wind_adjustment = d.windage_adjustment.get_in(unit.AngularMOA) if distance.v > 1 else None
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

The online version of Go documentation is located here: https://godoc.org/github.com/gehtsoft-usa/go_ballisticcalc

C# version of the package is located here: https://github.com/gehtsoft-usa/BallisticCalculator1

The online version of C# API documentation is located here: https://gehtsoft-usa.github.io/BallisticCalculator/web-content.html

Go documentation can be obtained using godoc tool.

The current status of the project is ALPHA version.

RISK NOTICE

The library performs very limited simulation of a complex physical process and so it performs a lot of approximations. Therefore the calculation results MUST NOT be considered as completely and reliably reflecting actual behavior or characteristics of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.

THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.
