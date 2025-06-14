after refactoring of cythonized _TrajectoryDataFilter

| Entry Name                |  Is Default?   | Relative Performance to Euler Engine | Additional dependencies  | Description                                                                                                                  |
|:--------------------------|:--------------:|:-------------------------------------|:-------------------------|:-----------------------------------------------------------------------------------------------------------------------------|
| `euler_engine`            | :green_circle: | Baseline (1x)                        | None                     | Standard Euler integration. A basic and generally lower-performing method.                                                   |
| `rk4_engine`              |  :red_circle:  | 0.54x (slower)                       | None                     | Standard Runge-Kutta 4th order integration. Typically more accurate than Euler, but slower in pure Python.                   |
| `cythonized_euler_engine` |  :red_circle:  | 49.40x faster                        | `py-ballisticcalc[exts]` | Cython-optimized Euler integration. Offers high performance due to Cython compilation.                                       |
| `cythonized_rk4_engine`   |  :red_circle:  | 71.64x faster                        | None                     | Cython-optimized Runge-Kutta 4th order integration. Provides very high performance.                                          |
| `scipy_engine` **(BETA)** |  :red_circle:  | 29.11x faster                        | `scipy`                  | Utilizes SciPy's numerical integration capabilities. Performance benefits from SciPy's optimized underlying implementations. |
