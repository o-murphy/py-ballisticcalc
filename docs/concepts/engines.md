# Engines

## Summary

py-ballisticcalc provides various calculation engines with identical public semantics.  The relative merits of the engines are detailed in [benchmarks](benchmarks.md).

| Engine Name                                                                         | Speed (Find Zero / Trajectory)                |        Dependencies         | Description                             |
| :---------------------------------------------------------------------------------- | :-------------------------------------------- | :-------------------------: | :-------------------------------------- |
| **[`rk4_engine`][py_ballisticcalc.engines.RK4IntegrationEngine]**                   | Baseline (1x)                                 |        None; default        | Runge-Kutta 4th-order integration       |
| [`euler_engine`][py_ballisticcalc.engines.EulerIntegrationEngine]                   | :material-arrow-down:    0.5x / 0.5x (slower) |            None             | Euler 1st-order integration             |
| [`verlet_engine`][py_ballisticcalc.engines.VelocityVerletIntegrationEngine]         | :material-arrow-down:   0.8x / 0.8x (slower)  |            None             | Verlet 2nd-order symplectic integration |
| [`cythonized_rk4_engine`][py_ballisticcalc_exts.CythonizedRK4IntegrationEngine]     | :material-arrow-up:   112x / 200x (faster)    | [`[exts]`](#cython-engines) | Compiled Runge-Kutta 4th-order          |
| [`cythonized_euler_engine`][py_ballisticcalc_exts.CythonizedEulerIntegrationEngine] | :material-arrow-up:    47x / 65x (faster)     | [`[exts]`](#cython-engines) | Compiled Euler integration              |
| [`scipy_engine`][py_ballisticcalc.engines.SciPyIntegrationEngine]                   | :material-arrow-up:   6.2x / 5.8x (faster)    |          `[scipy]`          | Advanced numerical methods              |


* This project will default to the [`rk4_engine`][py_ballisticcalc.engines.RK4IntegrationEngine].
* For higher speed and precision use the [`scipy_engine`][py_ballisticcalc.engines.SciPyIntegrationEngine].
* For maximum speed use the [`cythonized_rk4_engine`][py_ballisticcalc_exts.CythonizedRK4IntegrationEngine].

To select a specific engine when creating a [`Calculator`][py_ballisticcalc.interface.Calculator], use the optional `engine` argument:

```python
from py_ballisticcalc import Calculator
calc = Calculator(engine="rk4_engine")
# or via entry-point path
calc = Calculator(engine="my_pkg.my_mod:MyEngine")
```

## Cython Engines

Cythonized engines are compiled for maximum performance.  Include the `[exts]` option to install those:

=== "pip"
    ```bash
    pip install "py-ballisticcalc[exts]"
    ```
    
=== "uv"
    ```bash
    uv add py-ballisticcalc[exts]
    ```

## Custom Engines

**To define a custom engine:** Create a separate module with a class that implements the [`EngineProtocol`][py_ballisticcalc.generics.engine.EngineProtocol].
The engine's constructor should implement [`EngineFactoryProtocol`][py_ballisticcalc.generics.engine.EngineFactoryProtocol]
You can then load it like:
```python
from py_ballisticcalc import Calculator

calc = Calculator(engine="my_library.my_module:MyAwesomeEngine")
```

**Entry Point:** You can also give the engine a named entry point in `pyproject.toml`/`setup.py`.  The entry point name should end with `_engine`.  Example:

```toml
[project.entry-points.py_ballisticcalc]
my_awesome_engine = "my_library.my_module:MyAwesomeEngine"
```

Then you can load the engine using the entry point name:
```python
from py_ballisticcalc import Calculator

calc = Calculator(engine="my_awesome_engine")
```

**Test a custom engine**

To test a specific engine with the project test suite, run `pytest` with `--engine` argument.  Examples:
```shell
pytest ./tests --engine="my_awesome_engine" 
# or
pytest ./tests --engine="my_library.my_module:MyAwesomeEngine" 
```
