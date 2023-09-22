# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3.9+)

### Table of contents
* [Instalation](#installation)
* [Usage](#usage)
  * [Units of measure](#unit-manipulation-syntax)
  * [Simple usage examle](#example-of-library-usage)
* [About project](#about-project)

### Installation
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


### Usage

#### Unit manipulation syntax:
```python
from py_ballisticcalc.unit import *

# define var
unit_in_meter = Distance(100, Distance.Meter)
# >>> <Distance>: 100.0 m (3937.0078740157483)

# convert unit
unit_in_yards = unit_in_meter << Distance.Yard  # <<= operator also supports
# >>> <Distance>: 109.36132983377078 yd (3937.0078740157483)

# get value in specified units
value_in_km = unit_in_yards >> Distance.Kilometer  # >>= operator also supports
# >>> 0.1
```

#### Example of library usage
```python
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


# format output
def fmt(v: AbstractUnit, u: Unit):
    return f"{v >> u:.{u.accuracy}f} {u.symbol}"


# print output data
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
```

About project
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
