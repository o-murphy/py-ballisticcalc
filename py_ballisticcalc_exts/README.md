# BallisticCalculator
LGPL library for small arms ballistic calculations (Python 3.9+)

### Table of contents
* **[Installation](#installation)**
  * [Latest stable](#latest-stable-release-from-pypi)
  * [From sources](#installing-from-sources)
  * [Clone and build](#clone-and-build)
* **[Usage](#usage)**
  * [Units of measure](#unit-manipulation-syntax)
  * [An example of calculations](#an-example-of-calculations)
  * [Output example](#example-of-the-formatted-output)
* **[Older versions]()**
  * [v1.0.x](https://github.com/o-murphy/py_ballisticcalc/tree/v1.0.12)
* **[Contributors](#contributors)**
* **[About project](#about-project)**

### Installation
#### Latest stable release from pypi**
```shell
pip install py-ballisticcalc

# Using precompiled backend (improves performance)
pip install py-ballisticcalc[exts]

# Using matplotlib and pandas uses additional dependencies
pip install py-ballisticcalc[charts]
```


#### Using matplotlib and pandas uses additional dependencies
```shell
pip install py-ballisticcalc[charts]
```
#### Installing from sources
**MSVC** or **GCC** required
* Download and install **MSVC** or **GCC** depending on target platform
* Use one of the references you need:
```shell
# no binary from PyPi
pip install py-ballisticcalc==<version> --no-binary py-ballisticcalc

# master brunch
pip install git+https://github.com/o-murphy/py_ballisticcalc

# specific branch
pip install git+https://github.com/o-murphy/py_ballisticcalc.git@<target_branch_name>
```

[//]: # (#### Clone and build)

[//]: # (**MSVC** or **GCC** required)

[//]: # (```shell)

[//]: # (git clone https://github.com/o-murphy/py_ballisticcalc)

[//]: # (cd py_ballisticcalc)

[//]: # (python -m venv venv)

[//]: # (. venv/bin/activate)

[//]: # (pip install cython)

[//]: # (python setup.py build_ext --inplace)

[//]: # (```)

## Usage



The library supports all the popular units of measurement, and adds different built-in methods to define and manipulate it
#### Unit manipulation syntax:

```python
from py_ballisticcalc.unit import *

# ways to define value in prefer_units
# 1. old syntax
unit_in_meter = Distance(100, Distance.Meter)
# 2. short syntax by Unit type class
unit_in_meter = Distance.Meter(100)
# 3. by Unit enum class
unit_in_meter = Unit.Meter(100)

# >>> <Distance>: 100.0 m (3937.0078740157483)

# convert unit
# 1. by method
unit_in_yard = unit_in_meter.convert(Distance.Yard)
# 2. using shift syntax
unit_in_yards = unit_in_meter << Distance.Yard  # '<<=' operator also supports
# >>> <Distance>: 109.36132983377078 yd (3937.0078740157483)

# get value in specified prefer_units
# 1. by method
value_in_km = unit_in_yards.get_in(Distance.Kilometer)
# 2. by shift syntax
value_in_km = unit_in_yards >> Distance.Kilometer  # '>>=' operator also supports
# >>> 0.1

# getting unit raw value:
rvalue = Distance.Meter(10).raw_value
rvalue = float(Distance.Meter(10))

# prefer_units comparison:
# supports operators like < > <= >= == !=
Distance.Meter(100) == Distance.Centimeter(100)  # >>> False, compare two prefer_units by raw value
Distance.Meter(100) > 10  # >>> True, compare unit with float by raw value
```

#### An example of calculations

```python
from py_ballisticcalc import *
from py_ballisticcalc import Settings, PreferredUnits

# Modify default prefer_units
PreferredUnits.velocity = Velocity.FPS
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter

Settings.USE_POWDER_SENSITIVITY = True  # Correct muzzle velocity for powder temperature

# Define ammunition parameters
weight, diameter = 168, 0.308  # Numbers will be assumed to use default Settings.Units
length = Distance.Inch(1.282)  # Or declare prefer_units explicitly
dm = DragModel(0.223, TableG7, weight, diameter, length)
ammo = Ammo(dm, 2750, 15)
ammo.calc_powder_sens(2723, 0)
gun = Weapon(sight_height=9, twist=12)
current_atmo = Atmo(110, 29.8, 15, 72)
current_winds = [Wind(2, 90)]
shot = Shot(weapon=gun, ammo=ammo, atmo=current_atmo, winds=current_winds)
calc = Calculator()
calc.set_weapon_zero(shot, Distance.Meter(100))

shot_result = calc.fire(shot, trajectory_range=1000, trajectory_step=100)

for p in shot_result:
    print(p.formatted())
```
#### Example of the formatted output:
```shell
python -m py_ballisticcalc.example
```

```
('0.000 s', '0.0 m', '2750.0 ft/s', '2.46 mach', '-3.5 inch', '-3.5 inch', '0.00 mil', '0.0 inch', '0.00 mil', '0.0 m', '0.0939 °', '-4.062e-03', '0.000', '2821 ft·lb', '880 lb', 8)
('0.125 s', '100.1 m', '2526.5 ft/s', '2.26 mach', '0.0 inch', '0.0 inch', '0.00 mil', '0.2 inch', '0.05 mil', '100.1 m', '0.0068 °', '-4.062e-03', '0.665', '2381 ft·lb', '683 lb', 9)
('0.260 s', '200.0 m', '2313.5 ft/s', '2.07 mach', '-3.0 inch', '-3.0 inch', '-0.39 mil', '0.8 inch', '0.10 mil', '200.0 m', '-0.0967 °', '-4.062e-03', '0.633', '1996 ft·lb', '524 lb', 8)
('0.409 s', '300.1 m', '2111.2 ft/s', '1.89 mach', '-13.8 inch', '-13.8 inch', '-1.19 mil', '1.9 inch', '0.16 mil', '300.1 m', '-0.2207 °', '-4.062e-03', '0.599', '1663 ft·lb', '398 lb', 8)
('0.572 s', '400.1 m', '1919.6 ft/s', '1.72 mach', '-33.9 inch', '-33.9 inch', '-2.19 mil', '3.5 inch', '0.22 mil', '400.1 m', '-0.3701 °', '-4.062e-03', '0.570', '1374 ft·lb', '299 lb', 8)
('0.751 s', '500.0 m', '1736.8 ft/s', '1.56 mach', '-65.4 inch', '-65.4 inch', '-3.38 mil', '5.7 inch', '0.30 mil', '500.0 m', '-0.5516 °', '-4.062e-03', '0.545', '1125 ft·lb', '222 lb', 8)
('0.951 s', '600.1 m', '1561.9 ft/s', '1.40 mach', '-110.7 inch', '-110.7 inch', '-4.77 mil', '8.7 inch', '0.37 mil', '600.1 m', '-0.7748 °', '-4.062e-03', '0.521', '910 ft·lb', '161 lb', 8)
('1.173 s', '700.0 m', '1395.2 ft/s', '1.25 mach', '-173.1 inch', '-173.1 inch', '-6.40 mil', '12.6 inch', '0.47 mil', '700.0 m', '-1.0525 °', '-4.062e-03', '0.495', '726 ft·lb', '115 lb', 8)
('1.423 s', '800.0 m', '1238.1 ft/s', '1.11 mach', '-257.0 inch', '-257.0 inch', '-8.31 mil', '17.6 inch', '0.57 mil', '800.0 m', '-1.4030 °', '-4.062e-03', '0.462', '572 ft·lb', '80 lb', 8)
('1.705 s', '900.1 m', '1097.8 ft/s', '0.98 mach', '-368.2 inch', '-368.2 inch', '-10.58 mil', '24.1 inch', '0.69 mil', '900.1 m', '-1.8503 °', '-9.633e-03', '0.333', '450 ft·lb', '56 lb', 8)
```

## Contributors
### This project exists thanks to all the people who contribute.
#### Special thanks to:
- **[David Bookstaber](https://github.com/dbookstaber)** - Ballistics Expert, Financial Engineer \
*For the help in understanding and improvement of some calculation methods*
- **[Nikolay Gekht](https://github.com/nikolaygekht)** \
*For the sources code on C# and GO-lang from which this project firstly was forked from*

## About project

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

#### RISK NOTICE

The library performs very limited simulation of a complex physical process and so it performs a lot of approximations. Therefore, the calculation results MUST NOT be considered as completely and reliably reflecting actual behavior or characteristics of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.

THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.
