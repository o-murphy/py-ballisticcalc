# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3)

Installation
------------
    # stable release from pypi
    pip install py-ballisticcalc

    # latest release, may contain some issues
    pip install git+https://github.com/o-murphy/py_ballisticcalc

Usage example
-----
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
