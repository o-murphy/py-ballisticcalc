# Engines

py-ballisticcalc provides multiple integration engines with identical public semantics. Choose based on your needs for speed and dependencies:

- `rk4_engine`: Default Python RK4 (4th order) – balanced accuracy and simplicity.
- `euler_engine`: Simple 1st-order integrator – easiest to understand.
- `verlet_engine`: Velocity-Verlet 2nd-order – alternative numeric behavior.
- `scipy_engine`: High-quality ODE solvers from SciPy – fast and adaptive; requires `scipy`.
- `cythonized_rk4_engine` / `cythonized_euler_engine`: Cython-optimized variants – very fast; requires `py-ballisticcalc[exts]`.

Select an engine when creating `Calculator`:

```python
from py_ballisticcalc import Calculator
calc = Calculator(engine="rk4_engine")
# or via entry-point path
calc = Calculator(engine="my_pkg.my_mod:MyEngine")
```

See also: [BenchmarkEngines](https://github.com/o-murphy/py_ballisticcalc/blob/main/doc/BenchmarkEngines.md) for performance comparisons.

