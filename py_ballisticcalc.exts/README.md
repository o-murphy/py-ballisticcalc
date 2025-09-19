# BallisticCalculator

LGPL library for small arms ballistic calculations based on point-mass (3 DoF) plus spin drift.

[![license]][LGPL-3]
[![pypi]][PyPiUrl]
[![pypi-pre]][pypi-pre-url]
[![downloads]][pepy]
[![downloads/month]][pepy]
[![coverage]][coverage]
[![py-versions]][sources]
[![Made in Ukraine]][SWUBadge]

[![Pytest Euler (Cython)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-euler-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-euler-engine.yml)
[![Pytest RK4 (Cython)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-rk4-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-rk4-engine.yml)
[![Pytest Scipy](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-scipy-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-scipy-engine.yml)

[sources]:
https://github.com/o-murphy/py-ballisticcalc

[license]:
https://img.shields.io/github/license/o-murphy/py-ballisticcalc?style=flat-square

[LGPL-3]:
https://opensource.org/licenses/LGPL-3.0-only

[pypi]:
https://img.shields.io/pypi/v/py-ballisticcalc?style=flat-square&logo=pypi

[PyPiUrl]:
https://pypi.org/project/py-ballisticcalc/

[pypi-pre]:
https://img.shields.io/github/v/release/o-murphy/py-ballisticcalc?include_prereleases&style=flat-square&logo=pypi&label=pypi%20pre

[pypi-pre-url]:
https://pypi.org/project/py-ballisticcalc/#history

[coverage]:
https://github.com/o-murphy/py-ballisticcalc/coverage.svg

[downloads]:
https://img.shields.io/pepy/dt/py-ballisticcalc?style=flat-square

[downloads/month]:
https://static.pepy.tech/personalized-badge/py-ballisticcalc?style=flat-square&period=month&units=abbreviation&left_color=grey&right_color=blue&left_text=downloads%2Fmonth

[pepy]:
https://pepy.tech/project/py-ballisticcalc

[py-versions]:
https://img.shields.io/pypi/pyversions/py-ballisticcalc?style=flat-square

[Made in Ukraine]:
https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7&style=flat-square

[SWUBadge]:
https://stand-with-ukraine.pp.ua

[DOCUMENTATION]:
https://o-murphy.github.io/py-ballisticcalc

### Contents

* **[Installation](#installation)**
    * [Latest stable](https://pypi.org/project/py-ballisticcalc/)

  [//]: # (  * [From sources]&#40;#installing-from-sources&#41;)
  [//]: # (  * [Clone and build]&#40;#clone-and-build&#41;)

* **[QuickStart](#quickstart)**

    * [Examples](#examples)
    * [Ballistic Concepts](#ballistic-concepts)
    * [Units](#units)
    * [Calculation Engines](#calculation-engines)

* **[Documentation][DOCUMENTATION]**
* **[Contributors](#contributors)**
* **[About project](#about-project)**

# Installation

## pip

```shell
pip install py-ballisticcalc

# Include compiled engines
pip install py-ballisticcalc[exts]

# Include support for charting and dataframes
pip install py-ballisticcalc[charts]

# Get everything, including the SciPy engine
pip install pyballistic[exts,charts,scipy]
```

----

# [QuickStart](https://o-murphy.github.io/py-ballisticcalc/latest/)

## [Examples](https://github.com/o-murphy/py-ballisticcalc/blob/master/examples/Examples.ipynb)
  * [Extreme Examples](https://github.com/o-murphy/py-ballisticcalc/blob/master/examples/ExtremeExamples.ipynb)

## [Ballistic Concepts](https://o-murphy.github.io/py-ballisticcalc/latest/concepts)
  * [Coordinates](https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#coordinates)
  * [Slant / Look Angle](https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#look-angle)
  * [Danger Space](https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#danger-space)

## [Units](https://o-murphy.github.io/py-ballisticcalc/latest/concepts/unit)

Work in your preferred terms with easy conversions for the following dimensions and units:
* **Angular**: radian, degree, MOA, mil, mrad, thousandth, inch/100yd, cm/100m, o'clock
* **Distance**: inch, foot, yard, mile, nautical mile, mm, cm, m, km, line
* **Energy**: foot-pound, joule
* **Pressure**: mmHg, inHg, bar, hPa, PSI
* **Temperature**: Fahrenheit, Celsius, Kelvin, Rankine
* **Time**: second, minute, millisecond, microsecond, nanosecond, picosecond
* **Velocity**: m/s, km/h, ft/s, mph, knots
* **Weight**: grain, ounce, gram, pound, kilogram, newton


## [Calculation Engines](https://o-murphy.github.io/py-ballisticcalc/latest/concepts/engines)

Choose between different calculation engines, or build your own.  Included engines:

| Engine Name               |   Speed        | Dependencies    | Description                    |
|:--------------------------|:--------------:|:---------------:|:-------------------------------|
| `rk4_engine`              | Baseline (1x)  | None, default   | Runge-Kutta 4th-order integration  |
| `euler_engine`            |  0.5x (slower) | None            | Euler 1st-order integration |
| `verlet_engine`           |  0.7x (slower) | None            | Verlet 2nd-order integration |
| `cythonized_rk4_engine`   | 50x (faster)   | `[exts]`        | Compiled Runge-Kutta 4th-order |
| `cythonized_euler_engine` | 40x (faster)   | `[exts]`        | Compiled Euler integration |
| `scipy_engine`            | 10x (faster)   | `scipy`         | Advanced numerical methods |


# About project

The library provides trajectory calculation for ballistic projectiles launched by airguns, bows, firearms, artillery, etc.

The core point-mass (3DoF) ballistic model underlying this project was used on the earliest digital computers.  Robert McCoy (author of *Modern Exterior Ballistics*) implemented one in BASIC.  [JBM published code in C](https://www.jbmballistics.com/ballistics/downloads/downloads.shtml). Nikolay Gekht ported that to [C#](https://gehtsoft-usa.github.io/BallisticCalculator/web-content.html), extended it with formulas from Bryan Litz's _Applied Ballistics_, and ported it to [Go](https://godoc.org/github.com/gehtsoft-usa/go_ballisticcalc), while
Alexandre Trofimov implemented a calculator in [JavaScript](https://ptosis.ch/ebalka/ebalka.html).

This Python3 implementation has been expanded to support multiple ballistic coefficients and custom drag functions, such as those derived from Doppler radar data.

## Contributors

**This project exists thanks to all the people who contribute.**

<a href="https://github.com/o-murphy/py_ballisticcalc/graphs/contributors"><img height=32 src="https://contrib.rocks/image?repo=o-murphy/py_ballisticcalc" /></a>

Special thanks to:

* **[David Bookstaber](https://github.com/dbookstaber)** - Ballistics Expert <br>
*For help understanding and improving the functionality*
* **[Serhiy Yevtushenko](https://github.com/serhiy-yevtushenko)** - Applied Mathematician <br>
*For helping in consultations, testing, and improving edge case compatibility*
* **[Nikolay Gekht](https://github.com/nikolaygekht)** <br>
*For the source code in C# and GO-lang from which this project firstly was forked*

[//]: # (## Sister projects)

[//]: # ()

[//]: # (* **Py-BalCalc** - GUI App for [py_ballisticcalc]&#40;https://github.com/o-murphy/py_ballisticcalc&#41; solver library and profiles editor)

[//]: # (* **eBallistica** - Kivy based mobile App for ballistic calculations)

[//]: # ()

[//]: # (* <img align="center" height=32 src="https://github.com/JAremko/ArcherBC2/blob/main/resources/skins/sol-dark/icons/icon-frame.png?raw=true" /> [ArcherBC2]&#40;https://github.com/JAremko/ArcherBC2&#41; and [ArcherBC2 mobile]&#40;https://github.com/ApodemusSylvaticus/archerBC2_mobile&#41; - Ballistic profile editors)

[//]: # (  - *See also [a7p_transfer_example]&#40;https://github.com/JAremko/a7p_transfer_example&#41; or [a7p]&#40;https://github.com/o-murphy/a7p&#41; repo to get info about the ballistic profile format*)

## RISK NOTICE

This library performs approximate simulations of complex physical processes.
Therefore, the calculation results MUST NOT be considered as completely and reliably reflecting actual behavior of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.

THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.
