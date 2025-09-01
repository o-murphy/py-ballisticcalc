# Project Overview

`py_ballisticcalc` is a package of ballistic calculators and associated utilities.  The primary project is in Python.  There is a subproject called `py_ballisticcalc.exts` (in the subfolder of the same name) written in Cython and tuned for maximum performance, intended to duplicate the most established and popular features.  However it has not been as carefully designed or tested, so refer to the pure Python version for "truth."

The core project has a number of interchangeable "engines" that implement the `EngineProtocol`.  You can list them via:
```python
from py_ballisticcalc.interface import _EngineLoader
print("\nAvailable engines: " + str(sorted([e.name for e in _EngineLoader.iter_engines()])))
```

Both projects have tests in their root `/tests` folder.  The Cython tests only cover things unique to the Cython subproject.

The main project will only run tests for one engine at a time.  The default engine is the pure Python `rk4_engine`.  To specify the engine to test, use the `--engine` option with `pytest`.  Example:
```shell
pytest tests --engine="cythonized_rk4_engine"
```

## Terminal Usage

* Always ensure that you have activated the virtual environment.  `.venv\Scripts\activate`
* Always ensure that you are in the right folder.
  * Project root is `py-ballisticcalc`.
  * Cython subproject root is `py-ballisticcalc\py_ballisticcalc.exts`

## Cython

To build the Cython project, from the root of the Cython subproject (`py-ballisticcalc\py_ballisticcalc.exts`), run:
```shell
pip install -e .
```

## Permissions
* When you write and run scripts that are not candidates for inclusion in the public project, please put them in the git-excluded `debug` folder.
* You can do any internet searches to support requests.
* Do not git commit any code locally without explicit permission.
* Never git push or pull-request.
