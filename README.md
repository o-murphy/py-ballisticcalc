<h1 style="display: flex; align-items: center; gap: 10px;">
  <img src="./docs/favicon.svg" alt="favicon" width="50" height="50"> 
  Ballistic Solver Library
</h1>

LGPL library for small arms ballistic calculations based on point-mass (3 DoF) plus spin drift.

[![license]][LGPL-3]
[![pypi]][PyPiUrl]
[![pypi-pre]][pypi-pre-url]
[![downloads]][pepy]
[![downloads/month]][pepy]
[![coverage]][CodecovUrl]
[![py-versions]][sources]
[![Made in Ukraine]][SWUBadge]

[![powered by bclibc]][bclibc]
[![powered by pyodide]][Pyodide]

[![Pre-commit](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pre-commit.yml)
[![Pytest RK4](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-rk4-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-rk4-engine.yml)
[![Python Euler](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-euler-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-euler-engine.yml)
[![Pytest Euler (Cython)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-euler-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-euler-engine.yml)
[![Pytest RK4 (Cython)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-rk4-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-rk4-engine.yml)
[![Pytest Verlet (Cython)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-verlet-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-cythonized-verlet-engine.yml)
[![Pytest Scipy](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-scipy-engine.yml/badge.svg)](https://github.com/o-murphy/py-ballisticcalc/actions/workflows/pytest-scipy-engine.yml)


### Contents

* **[Installation](#installation)**
    * [Latest stable][PyPiUrl]

  [//]: # (  * [From sources]&#40;#installing-from-sources&#41;)
  [//]: # (  * [Clone and build]&#40;#clone-and-build&#41;)

* **[Quick Start](#quick-start)**
    * [Interactive Web REPL](#interactive-web-repl)
    * [Examples](#examples)
    * [Ballistic Concepts](#ballistic-concepts)
    * [Units](#units)
    * [Calculation Engines](#calculation-engines)

* **[Documentation][DOCUMENTATION]**
* **[Contributors](#contributors)**
* **[About project](#about-project)**

## Installation

### uv

```shell
uv add py-ballisticcalc

# Using precompiled backend (improves performance)
uv add py-ballisticcalc[exts]

# Using matplotlib and pandas uses additional dependencies
uv add py-ballisticcalc[charts]

# Get everything, including the SciPy engine
uv add py-ballisticcalc[exts,charts,scipy]
```

### pip

```shell
pip install py-ballisticcalc

# Using precompiled backend (improves performance)
pip install py-ballisticcalc[exts]

# Using matplotlib and pandas uses additional dependencies
pip install py-ballisticcalc[charts]

# Get everything, including the SciPy engine
pip install py-ballisticcalc[exts,charts,scipy]
```

----


## [Quick Start] - click here to open Quick Start guide

### [Interactive Web REPL]

<img src="https://raw.githubusercontent.com/pyodide/pyodide-artwork/refs/heads/main/logo-dark.svg" style="height: 32px; width: auto; background-color: black" />

Prefer to try it before installing anything? Open the [Interactive Web REPL] — runs entirely in your browser via [Pyodide].

### [Examples]
  * [Extreme Examples]

### [Ballistic Concepts]
  * [Coordinates]
  * [Slant / Look Angle]
  * [Danger Space]

### [Units]

Work in your preferred terms with easy conversions for the following dimensions and units:
* **Angular**: radian, degree, MOA, mil, mrad, thousandth, inch/100yd, cm/100m, o'clock
* **Distance**: inch, foot, yard, mile, nautical mile, mm, cm, m, km, line
* **Energy**: foot-pound, joule
* **Pressure**: mmHg, inHg, bar, hPa, PSI
* **Temperature**: Fahrenheit, Celsius, Kelvin, Rankine
* **Time**: second, minute, millisecond, microsecond, nanosecond, picosecond
* **Velocity**: m/s, km/h, ft/s, mph, knots
* **Weight**: grain, ounce, gram, pound, kilogram, newton


### [Calculation Engines]

Choose between different calculation engines, or build your own.  Included engines:

| Engine Name                                                                                   | Speed (Find Zero / Trajectory)                |        Dependencies         | Description                             |
| :-------------------------------------------------------------------------------------------- | :-------------------------------------------- | :-------------------------: | :-------------------------------------- |
| **[`rk4_engine`][py_ballisticcalc.engines.RK4IntegrationEngine]**                             | Baseline (1x)                                 |        None; default        | Runge-Kutta 4th-order integration       |
| [`euler_engine`][py_ballisticcalc.engines.EulerIntegrationEngine]                             | :material-arrow-down:    0.5x / 0.5x (slower) |            None             | Euler 1st-order integration             |
| [`verlet_engine`][py_ballisticcalc.engines.VelocityVerletIntegrationEngine]                   | :material-arrow-down:   0.8x / 0.8x (slower)  |            None             | Verlet 2nd-order symplectic integration |
| [`cythonized_rk4_engine`][py_ballisticcalc_exts.CythonizedRK4IntegrationEngine]               | :material-arrow-up:   112x / 200x (faster)    | [`[exts]`](#cython-engines) | Compiled Runge-Kutta 4th-order          |
| [`cythonized_euler_engine`][py_ballisticcalc_exts.CythonizedEulerIntegrationEngine]           | :material-arrow-up:    47x / 65x (faster)     | [`[exts]`](#cython-engines) | Compiled Euler integration              |
| [`cythonized_verlet_engine`][py_ballisticcalc_exts.CythonizedVelocityVerletIntegrationEngine] | :material-arrow-up:   157x / 100x (faster)    | [`[exts]`](#cython-engines) | Compiled Verlet 2nd-order symplectic    |
| [`scipy_engine`][py_ballisticcalc.engines.SciPyIntegrationEngine]                             | :material-arrow-up:   6.2x / 5.8x (faster)    |          `[scipy]`          | Advanced numerical methods              |


## About project

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


## Sister projects

* **[bclibc]** - High performance C++/C99 Ballistic solver engine
* **[micropython-bclibc]** - Pure C99 Ballistic Solver Engine for MicroPython ([bclibc] subset)
* **[ebalistyka]** - Ballistic Calculator built with Flutter and high performance C++ engine
* **[js-ballistics]** - ISC library for small arms ballistic calculations (JavaScript ES6+)


## License

Copyright (C) 2023 Yaroshenko Dmytro (o-murphy)

This library is free software: you can redistribute it and/or modify it under the terms of the **GNU Lesser General Public License v3.0** as published by the Free Software Foundation.

See [LICENSE](LICENSE) for the full text. See [CHANGELOG](CHANGELOG.md) for release history.

> [!NOTE]
> **[bclibc]** (the ballistic solver engine, located in `py_ballisticcalc_exts/external/bclibc`) is licensed separately under the **GNU Lesser General Public License v3.0**. See [`py_ballisticcalc_exts/external/bclibc/LICENSE`](py_ballisticcalc_exts/external/bclibc/LICENSE).


> [!WARNING]
>
> ## RISK NOTICE
>
> This library performs approximate simulations of complex physical processes.
> Therefore, the calculation results MUST NOT be considered as completely and reliably > reflecting actual behavior of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.
> 
> THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.


<!-- REUSABLE LINKS -->

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
https://codecov.io/gh/o-murphy/py-ballisticcalc/graph/badge.svg

[CodecovUrl]:
https://codecov.io/gh/o-murphy/py-ballisticcalc

[downloads]:
https://img.shields.io/pepy/dt/py-ballisticcalc?style=flat-square

[downloads/month]:
https://static.pepy.tech/personalized-badge/py-ballisticcalc?style=flat-square&period=month&units=abbreviation&left_color=grey&right_color=blue&left_text=downloads%2Fmonth

[pepy]: https://pepy.tech/project/py-ballisticcalc

[py-versions]:
https://img.shields.io/pypi/pyversions/py-ballisticcalc?style=flat-square

[Made in Ukraine]:
https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7&style=flat-square

[SWUBadge]:
https://stand-with-ukraine.pp.ua

<!-- DOCS -->

[DOCUMENTATION]:
https://o-murphy.github.io/py-ballisticcalc

[Quick Start]:
https://o-murphy.github.io/py-ballisticcalc/latest/

[Interactive Web REPL]:
https://o-murphy.github.io/py-ballisticcalc/latest/pyodide/

[Examples]:
https://github.com/o-murphy/py-ballisticcalc/blob/master/examples/Examples.ipynb

[Extreme Examples]:
https://github.com/o-murphy/py-ballisticcalc/blob/master/examples/ExtremeExamples.ipynb

[Ballistic Concepts]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts

[Coordinates]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#coordinates

[Slant / Look Angle]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#look-angle

[Danger Space]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts/#danger-space

[Units]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts/unit

[Calculation Engines]:
https://o-murphy.github.io/py-ballisticcalc/latest/concepts/engines

<!-- SISTERS PROJECTS -->


[bclibc]: https://github.com/ballistics-lab/bclibc
[micropython-bclibc]: https://github.com/ballistics-lab/micropython-bclibc
[ebalistyka]: https://github.com/o-murphy/ebalistyka-app
[js-ballistics]: https://github.com/o-murphy/js-ballistics


<!-- CUSTOM BADGES -->


[powered by bclibc]:
https://img.shields.io/badge/bclibc-0d1228?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI%2FPgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIgImh0dHA6Ly93d3cudzMub3JnL1RSLzIwMDEvUkVDLVNWRy0yMDAxMDkwNC9EVEQvc3ZnMTAuZHRkIj4KPHN2ZyB2ZXJzaW9uPSIxLjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjEwMjQuMDAwMDAwcHQiIGhlaWdodD0iMTAyNC4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDEwMjQuMDAwMDAwIDEwMjQuMDAwMDAwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0Ij4KCTxjaXJjbGUgY3g9IjUxMiIgY3k9IjUxMiIgcj0iNTEyIiBmaWxsPSIjMGQxMjI4IiAvPgoJPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTEwMCwxMTI0KSBzY2FsZSgwLjEyMDAwMCwtMC4xMjAwMDApIiBmaWxsPSIjRkZGRkZGIiBzdHJva2U9Im5vbmUiPgoJCTxwYXRoIGQ9Ik01MDU1IDgwNzEgYy0xNjcgLTMzMyAtMjczIC03NjggLTI5MiAtMTE5OCBsLTYgLTE0MyAzNDYgMCAzNDcgMCAwCjYzIGMwIDI3NSAtODAgNzMxIC0xNzUgMTAwNyAtMzkgMTEyIC0xNDUgMzQzIC0xNjMgMzU0IC03IDQgLTI5IC0yOCAtNTcgLTgzegptLTE1IC0yODkgYy00NiAtMjI1IC05MCAtNjYzIC05MCAtODk0IDAgLTEwNCAtMiAtMTA4IC02MSAtMTA4IGwtNDkgMCAwIDc4CmMxIDE1OSA0OCA0ODIgMTAxIDY5MCAzNCAxMzQgMTE5IDM5NiAxMjUgMzg5IDMgLTMgLTkgLTcyIC0yNiAtMTU1eiIgLz4KCQk8cGF0aCBkPSJNNDcxMCA2NDA2IGwwIC0yNDQgMjMgLTYgYzEyIC0zIDMyIC02IDQ1IC02IGwyMiAwIDAgMjI1IDAgMjI1IDY1IDAKNjUgMCAwIC0yMjUgMCAtMjI1IDI4MyAyIDI4MiAzIDMgMjQ4IDIgMjQ3IC0zOTUgMCAtMzk1IDAgMCAtMjQ0eiIgLz4KCQk8cGF0aCBkPSJNNDQyNCA2MTExIGMtMTggLTUgLTQ4IC0xOCAtNjggLTMwIC0xMzcgLTg1IC0xMjAgLTMwMCAyOSAtMzcwIGw0NgotMjEgLTMgLTUzMyAtMyAtNTMyIC0yMyAtNTggYy0xOCAtNDUgLTU0NSAtODUwIC04NzkgLTEzNDMgLTc2IC0xMTMgLTExMgotMjkxIC04MyAtNDE1IDQxIC0xNzcgMTY5IC0zMTIgMzQwIC0zNTkgNTkgLTE3IDI1OTMgLTE1IDI2NTUgMiAxMTQgMzAgMjMzCjEyMiAyODcgMjI0IDc2IDE0MiA3NyAzNDMgMyA0ODYgLTI4IDU0IC0xMzMgMjEzIC01NzMgODc1IC0xNzYgMjY2IC0zMzEgNTA5Ci0zNDQgNTQwIC0yMyA1OCAtMjMgNjAgLTI2IDU4OCBsLTMgNTMwIDQ1IDE4IGM1MiAyMiAxMDEgODAgMTE3IDE0MSAyNCA5MAotMjMgMTk2IC0xMDYgMjM2IC01NCAyNiAtMTk5IDM1IC0yMDEgMTMgLTEgLTcgLTIgLTE3IC0zIC0yMiAwIC01IC04OCAtNwotMjA4IC0zIC0xNTQgNCAtMjA0IDIgLTE5OSAtNiA0IC03IDE1IC0xMiAyNiAtMTIgMTAgMCA5MiAtMTMgMTgxIC0yOSA5MCAtMTYKMjA2IC0zMyAyNTggLTM3IDEwOSAtNyAxNDEgLTI3IDE0MSAtODYgLTEgLTYwIC00OCAtOTggLTEyNSAtOTggbC00NiAwIDMKLTU5MiAzIC01OTMgMjUgLTcwIGMxOCAtNTIgODAgLTE1NCAyNDEgLTM5NSA0NzYgLTcxNCA2ODkgLTEwNDMgNzEwIC0xMDk3IDE2Ci00NCAyMiAtNzkgMjIgLTE0MyAwIC0xNzQgLTgxIC0yOTMgLTIzNyAtMzQ3IC00OCAtMTcgLTEyNSAtMTggLTEzMzEgLTE4CmwtMTI4MCAwIC02NSAzMSBjLTc5IDM4IC0xMzEgODkgLTE2OCAxNjMgLTI1IDUxIC0yNyA2NiAtMjcgMTcxIDAgOTggMyAxMjIKMjIgMTYzIDEzIDI3IDExNiAxODkgMjI5IDM2MCAxMTQgMTcyIDMwOCA0NjQgNDMyIDY1MCAxMjMgMTg1IDIzNiAzNjMgMjUyCjM5NSA1NCAxMTEgNTUgMTIwIDU1IDc0MiBsMCA1NzUgLTUwIDYgYy0yNyAzIC01OCA5IC02OCAxNCAtMjcgMTEgLTQ5IDYyIC00Mgo5NCAxMCA0OCA0MyA2OSAxMTAgNzMgbDYwIDMgMCA2MCAwIDYwIC01MCAyIGMtMjcgMSAtNjQgLTIgLTgxIC02eiIgLz4KCQk8cGF0aCBkPSJNNDcwMCA1MzY5IGMwIC00MjggLTQgLTcwNyAtMTEgLTc1MiAtMjMgLTE1NyAtNTggLTIzMCAtMjYzIC01NDAKLTg0IC0xMjggLTE5NSAtMjk3IC0yNDggLTM3NyAtNTIgLTgwIC0xNjYgLTI1MyAtMjUzIC0zODUgLTg3IC0xMzIgLTE2OSAtMjYwCi0xODIgLTI4NCAtNDMgLTgyIC0yNiAtMTk3IDM5IC0yNTggNTkgLTU2IC03IC01MyAxMzI3IC01MyBsMTIyOSAwIDUyIDI4IGM5OAo1MSAxMzIgMTc2IDc3IDI4MiAtMjMgNDUgLTI2MSA0MTAgLTYzMyA5NzUgLTIzOCAzNjEgLTI1OCAzOTUgLTMwMiA1NDQgLTE0CjQ5IC0xNyAxMzkgLTIyIDcxNiBsLTUgNjYwIC0xMTUgMTcgYy02MyAxMCAtMTg1IDI5IC0yNzEgNDMgLTIxNyAzNSAtMTk5IDM5Ci0xOTkgLTQ4IDAgLTQxIC00IC0xNTQgLTEwIC0yNTMgLTUgLTk4IC0xNyAtMzEyIC0yNSAtNDc0IC05IC0xNjIgLTIwIC0zNDcKLTI1IC00MTAgLTUgLTYzIC0xMCAtMTQ1IC0xMCAtMTgyIDAgLTM4IC00IC02OCAtOCAtNjggLTggMCAtMjggNTcwIC0zOSAxMTU3CmwtNiAzMzEgLTMwIDYgYy0xNiAzIC0zOCA2IC00OCA2IC0xOCAwIC0xOSAtMjIgLTE5IC02ODF6IG0xMDMyIC0xNDI2IGM5IC0xMAo3NCAtMTA2IDE0NCAtMjE1IDcxIC0xMDggMjAzIC0zMDkgMjk0IC00NDcgMjEwIC0zMTggMjAyIC0zMDUgMjA0IC0zNTMgMSAtMzIKLTUgLTQ1IC0yNyAtNjQgbC0yOCAtMjQgLTEyMTUgMCAtMTIxNSAwIC0yNCAyNSBjLTE5IDE4IC0yNSAzNSAtMjUgNjggMCA0MQoxNyA2OSAyMDYgMzU4IDExNCAxNzMgMjU5IDM5NCAzMjMgNDkxIGwxMTYgMTc4IDYxNiAwIGM1NzQgMCA2MTcgLTEgNjMxIC0xN3oiIC8%2BCgk8L2c%2BCjwvc3ZnPgo%3D&label=powered%20by

[Pyodide]: https://pyodide.org

[powered by pyodide]:
https://img.shields.io/badge/pyodide-%23654FF0?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8%2BCjxzdmcKICAgaWQ9IkxheWVyXzEiCiAgIGRhdGEtbmFtZT0iTGF5ZXIgMSIKICAgdmlld0JveD0iMCAwIDE4MiAxODIiCiAgIHZlcnNpb249IjEuMSIKICAgc29kaXBvZGk6ZG9jbmFtZT0ibG9nby1xdWFkcmF0aWMtZGFyay5zdmciCiAgIHdpZHRoPSIxODIiCiAgIGhlaWdodD0iMTgyIgogICBpbmtzY2FwZTp2ZXJzaW9uPSIxLjQuNCAoZGNhZjNlNywgMjAyNi0wNS0wNSkiCiAgIGlua3NjYXBlOmV4cG9ydC1maWxlbmFtZT0ibG9nby1xdWFkcmF0aWMtZGFyay5wbmciCiAgIGlua3NjYXBlOmV4cG9ydC14ZHBpPSI5NiIKICAgaW5rc2NhcGU6ZXhwb3J0LXlkcGk9Ijk2IgogICB4bWxuczppbmtzY2FwZT0iaHR0cDovL3d3dy5pbmtzY2FwZS5vcmcvbmFtZXNwYWNlcy9pbmtzY2FwZSIKICAgeG1sbnM6c29kaXBvZGk9Imh0dHA6Ly9zb2RpcG9kaS5zb3VyY2Vmb3JnZS5uZXQvRFREL3NvZGlwb2RpLTAuZHRkIgogICB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiAgIHhtbG5zOnN2Zz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxzb2RpcG9kaTpuYW1lZHZpZXcKICAgICBpZD0ibmFtZWR2aWV3MjciCiAgICAgcGFnZWNvbG9yPSIjZmZmZmZmIgogICAgIGJvcmRlcmNvbG9yPSIjNjY2NjY2IgogICAgIGJvcmRlcm9wYWNpdHk9IjEuMCIKICAgICBpbmtzY2FwZTpzaG93cGFnZXNoYWRvdz0iMiIKICAgICBpbmtzY2FwZTpwYWdlb3BhY2l0eT0iMC4wIgogICAgIGlua3NjYXBlOnBhZ2VjaGVja2VyYm9hcmQ9IjAiCiAgICAgaW5rc2NhcGU6ZGVza2NvbG9yPSIjZDFkMWQxIgogICAgIHNob3dncmlkPSJmYWxzZSIKICAgICBpbmtzY2FwZTp6b29tPSIxLjI5NjcwMzMiCiAgICAgaW5rc2NhcGU6Y3g9IjI0OS4wOTMyMiIKICAgICBpbmtzY2FwZTpjeT0iOTEuMzg1NTkzIgogICAgIGlua3NjYXBlOndpbmRvdy13aWR0aD0iMTkyMCIKICAgICBpbmtzY2FwZTp3aW5kb3ctaGVpZ2h0PSI5ODAiCiAgICAgaW5rc2NhcGU6d2luZG93LXg9IjAiCiAgICAgaW5rc2NhcGU6d2luZG93LXk9IjAiCiAgICAgaW5rc2NhcGU6d2luZG93LW1heGltaXplZD0iMSIKICAgICBpbmtzY2FwZTpjdXJyZW50LWxheWVyPSJMYXllcl8xIiAvPgogIDxkZWZzCiAgICAgaWQ9ImRlZnM0Ij4KICAgIDxzdHlsZQogICAgICAgaWQ9InN0eWxlMiI%2BCiAgICAgIC5jbHMtMSB7CiAgICAgICAgZmlsbDogI2ZmZjsKICAgICAgfQoKICAgICAgLmNscy0yIHsKICAgICAgICBmaWxsOiAjNjU0ZmYwOwogICAgICB9CiAgICA8L3N0eWxlPgogIDwvZGVmcz4KICA8cmVjdAogICAgIGNsYXNzPSJjbHMtMSIKICAgICB4PSIxMDciCiAgICAgeT0iMTI1IgogICAgIHdpZHRoPSI1MCIKICAgICBoZWlnaHQ9IjMyIgogICAgIGlkPSJyZWN0NiIgLz4KICA8cGF0aAogICAgIGNsYXNzPSJjbHMtMiIKICAgICBkPSJtIDEzNS4xOCw5NyBjIDAsLTAuMTMgLTAuMDEsLTcuMjQgLTAuMDIsLTcuMzcgaCAyNy41MSB2IDcxLjMzIEggOTEuMzMgViA4OS42MyBoIDI3LjUxIGMgMCwwLjEzIC0wLjAyLDcuMjQgLTAuMDIsNy4zNyBtIDMyLjU5LDU2LjMzIGggNC45IGwgLTcuNDMsLTI1LjI1IGggLTcuNDUgbCAtNi4xMiwyNS4yNSBoIDQuNzUgbCAxLjI0LC01LjYyIGggOC40OSBsIDEuNjEsNS42MiB6IG0gLTI2LjAzLDAgaCA0LjY5IGwgNi4wMiwtMjUuMjUgaCAtNC42MyBsIC0zLjY5LDE3LjQgaCAtMC4wNiBsIC0zLjUsLTE3LjQgaCAtNC40MiBsIC0zLjksMTcuMTkgaCAtMC4wNiBsIC0zLjIzLC0xNy4xOSBoIC00LjcyIGwgNS40NCwyNS4yNSBoIDQuNzggbCAzLjc1LC0xNy4xOSBoIDAuMDYgeiBtIDE4Ljg5LC0xOS4wMyBoIDEuOTkgbCAyLjM3LDkuMjcgaCAtNi40MiB6IgogICAgIGlkPSJwYXRoOCIgLz4KICA8ZwogICAgIGlkPSJnMjQiPgogICAgPHBhdGgKICAgICAgIGQ9Im0gODksNDkuNjYgYyAwLDEwLjYgLTguOCwyMCAtMjAsMjAgSCAyOSB2IDIwIEggMTkgdiAtNzAgaCA1MCBjIDEwLjcsMCAxOS43LDguOSAyMCwyMCB6IG0gLTEwLC0xMCBjIDAsLTUuNSAtNC41LC0xMCAtMTAsLTEwIEggMjkgdiAzMCBoIDQwIGMgNS41LDAgMTAsLTQuNSAxMCwtMTAgeiIKICAgICAgIGlkPSJwYXRoMTAiCiAgICAgICBzdHlsZT0iZmlsbDojZmZmZmZmO2ZpbGwtb3BhY2l0eToxIiAvPgogICAgPHBhdGgKICAgICAgIGQ9Im0gMTMyLDY3LjY2IHYgMjIgaCAtMTAgdiAtMjIgbCAtMzAsLTMzIHYgLTE1IGggMTAgdiAxMC45IGwgMjUsMjcuNSAyNSwtMjcuNSB2IC0xMC45IGggMTAgdiAxNSB6IgogICAgICAgaWQ9InBhdGgxMiIKICAgICAgIHN0eWxlPSJmaWxsOiNmZmZmZmY7ZmlsbC1vcGFjaXR5OjEiIC8%2BCiAgPC9nPgo8L3N2Zz4K&label=powered%20by&labelColor=black
