# Benchmarks

Mean time per call for each engine (lower is better), generated from
[`benchmarks/benchmarks.csv`](../../benchmarks/benchmarks.csv) by `scripts/bench_report.py`.
Each engine has two bars: `Trajectory` (fire a trajectory) and `Zero` (find the zero angle).
The vertical scales are logarithmic.

## Mean time

![Mean time per call by engine](bench.svg)

## Speedup vs `python.rk4`

![Speedup vs python.rk4](bench_speedup.svg)

- **Version:** `3.0.0b3.dev1+g68ceae077.d20260921` (branch `new-entry-points`, commit `513fd33`)
- Where an engine was run several times, the run with the most repeats is used.
- Only engines present in the benchmark data are listed.

## Results

| Engine | Trajectory, ms | vs `python.rk4` | Zero, ms | vs `python.rk4` | Repeats |
|--------|---------------:|-----------:|---------:|-----------:|--------:|
| `python.euler` | 115.079 | 0.518x | 516.899 | 0.504x | 50 |
| `python.verlet` | 77.055 | 0.773x | 346.689 | 0.752x | 50 |
| `python.rk4` | 59.557 | 1x | 260.625 | 1x | 50 |
| `scipy.lsoda` | 12.939 | 4.6x | 83.901 | 3.11x | 500 |
| `scipy.rk45` | 7.100 | 8.39x | 55.676 | 4.68x | 500 |
| `cython.euler` | 1.267 | 47x | 4.455 | 58.5x | 500 |
| `cython.rk4` | 0.429 | 139x | 1.179 | 221x | 1000 |
| `cython.dopri` | 0.170 | 350x | 0.094 | 2773x | 2000 |
| `cython.tsitouras` | 0.170 | 350x | 0.094 | 2773x | 2000 |
| `cython.rkck` | 0.170 | 350x | 0.094 | 2773x | 2000 |

!!! note
    Adaptive engines (`cython.rkck`, `cython.dopri`, `cython.tsitouras`) take far fewer steps than
    fixed-step RK4, which is why `Zero` shows such a large gap. Results depend on hardware and workload;
    treat them as relative figures. See [Engines](engines.md) for the engine overview.
