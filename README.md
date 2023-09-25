# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3.9+)

### Table of contents
* [Instalation](#installation)
* [Usage](#usage)
  * [Units of measure](#unit-manipulation-syntax)
  * [Simple usage examle](#example-of-library-usage)
  * [Output example](#example-of-the-formatted-output)
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
```
#### Example of the formatted output:
```
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
