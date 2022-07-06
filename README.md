# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3)

Installation
------------
**Stable release from pypi**
```commandline
pip install py-ballisticcalc
```
**Latest release, may contain some issues**
```commandline
pip install git+https://github.com/o-murphy/py_ballisticcalc
```    

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

**An extended class that includes support for custom drag and drop functionality and adds some more methods that not available in standard library classes**

```python
from py_ballisticcalc.extended import BallisticCoefficientExtended
```

**Convert multiple bc to custom drag table**
```python
from py_ballisticcalc.extended import MultipleBallisticCoefficient
from py_ballisticcalc.extended.profile_extended import *

multiple_bc = MultipleBallisticCoefficient([[0.275, 800], [0.26, 700], [0.255, 500], ],
                                   unit.VelocityMPS,
                                   DragTableG7,
                                   unit.Distance(0.308, unit.DistanceInch),
                                   unit.Weight(178, unit.WeightGrain))

table = multiple_bc.calculate_custom_drag_func()
```

**Using with custom drag table**
```python
from py_ballisticcalc.extended import ProfileExtended

custom_drag_func = [
    {'A': 0.0, 'B': 0.18}, {'A': 0.4, 'B': 0.178}, ... , {'A': 5.0, 'B': 0.18}
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

Now it's also ported to python3 and expanded to support calculation trajectory by 
multiple ballistics coefficients and using custom drag data (such as Doppler radar data ©Lapua, etc.)

The online version of Go documentation is located here: https://godoc.org/github.com/gehtsoft-usa/go_ballisticcalc

C# version of the package is located here: https://github.com/gehtsoft-usa/BallisticCalculator1

The online version of C# API documentation is located here: https://gehtsoft-usa.github.io/BallisticCalculator/web-content.html

Go documentation can be obtained using godoc tool.

The current status of the project is ALPHA version.

RISK NOTICE

The library performs very limited simulation of a complex physical process and so it performs a lot of approximations. Therefore the calculation results MUST NOT be considered as completely and reliably reflecting actual behavior or characteristics of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.

THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.
