# Engine Benchmark Report — py-ballisticcalc v2.2.2

**Date:** 2025-10-17  
**Branch:** `240-bump-to-python-314-dePython39`  
**Commit:** `dc8231e`  
**Reference engine:** `rk4_engine`  
**Repetitions:** 100  
**Environment:** Python 3.14 (CPython), GC suppressed during timing  

---

## 🧪 Test Conditions

Two fixed benchmark cases were executed for each integration engine:

| Case           | Description                                                                  |
| -------------- | ---------------------------------------------------------------------------- |
| **Trajectory** | Full ballistic trajectory integration to 2000 m, step 100 m (`TrajFlag.ALL`) |
| **Zero**       | Calculation of zero angle at 2000 m (`set_weapon_zero`)                      |

All runs used the same atmospheric, weapon, and ammunition setup:

- **Ammunition:** G7 model, 10 g bullet, 7.62 mm caliber  
- **Muzzle velocity:** 800 m/s  
- **Atmosphere:** ICAO standard  
- **Weapon sight height:** 4 cm  
- **Twist:** 30 cm  
- **Range:** 2000 m  

Each case was repeated 100 times after 10 warm-up iterations.  
Garbage collection was disabled during measurements to ensure consistent timing.

---

## 📊 Results

| Case       | Engine                  | Mean (ms)  | StdDev   | Min        | Max        |
| ---------- | ----------------------- | ---------- | -------- | ---------- | ---------- |
| Trajectory | euler_engine            | 167.87     | 2.03     | 165.25     | 176.12     |
| Zero       | euler_engine            | 774.55     | 4.27     | 766.32     | 795.35     |
| Trajectory | **rk4_engine**          | **80.12**  | **0.65** | **79.08**  | **83.09**  |
| Zero       | **rk4_engine**          | **382.72** | **1.49** | **379.18** | **390.29** |
| Trajectory | scipy_engine            | 18.27      | 0.30     | 17.99      | 20.31      |
| Zero       | scipy_engine            | 83.53      | 0.81     | 82.24      | 87.24      |
| Trajectory | cythonized_euler_engine | 50.70      | 0.41     | 49.91      | 53.12      |
| Zero       | cythonized_euler_engine | 9.37       | 0.11     | 9.16       | 9.73       |
| Trajectory | cythonized_rk4_engine   | 11.24      | 0.15     | 11.02      | 11.70      |
| Zero       | cythonized_rk4_engine   | 4.17       | 0.04     | 4.06       | 4.32       |
| Trajectory | verlet_engine           | 102.74     | 0.61     | 101.32     | 104.48     |
| Zero       | verlet_engine           | 486.16     | 2.24     | 481.90     | 490.52     |

---

## ⚙️ Performance Comparison (relative to `rk4_engine`)

# Engine Benchmark — py-ballisticcalc v2.2.2

**Date:** 2025-10-17  
**Branch:** `240-bump-to-python-314-dePython39`  
**Commit:** `dc8231e`  

Reference engine: **rk4_engine** (used for relative difference and speedup calculation)  
Repetitions: 100, GC suppressed during timing  

---

### Trajectory Case (2000 m, step 100 m)

| Engine                  | Mean Time (ms) | Speedup | Relative Difference (%) | Notes                                           |
| ----------------------- | -------------- | ------- | ----------------------- | ----------------------------------------------- |
| rk4_engine (Reference)  | 80.12          | 1.00×   | 0%                      | Base RK4 integrator                             |
| cythonized_rk4_engine   | 11.24          | 7.13×   | +613%                   | Fastest in this scenario; Cython optimization 🚀 |
| scipy_engine            | 18.27          | 4.38×   | +338%                   | Very fast due to external optimized libraries   |
| cythonized_euler_engine | 50.70          | 1.58×   | +58%                    | Cython optimization, but less accurate method   |
| verlet_engine           | 102.74         | 0.78×   | −22%                    | Slower than RK4 🐢                               |
| euler_engine            | 167.87         | 0.48×   | −52%                    | Slowest 🛑                                       |

---

### Zero Case (2000 m, set_weapon_zero)

| Engine                  | Mean Time (ms) | Speedup | Relative Difference (%) | Notes                                            |
| ----------------------- | -------------- | ------- | ----------------------- | ------------------------------------------------ |
| rk4_engine (Reference)  | 382.72         | 1.00×   | 0%                      | Base RK4 integrator                              |
| cythonized_rk4_engine   | 4.17           | 91.78×  | +9078%                  | Maximum speedup! Cythonization has huge effect 🚀 |
| cythonized_euler_engine | 9.37           | 40.84×  | +3984%                  | Fast, but still slower than Cythonized RK4       |
| scipy_engine            | 83.53          | 4.58×   | +358%                   | High performance, but behind Cython versions     |
| verlet_engine           | 486.16         | 0.79×   | −21%                    | Slower than RK4 🐢                                |
| euler_engine            | 774.55         | 0.49×   | −51%                    | Slowest 🛑                                        |

## 🧭 Summary

- The **Cythonized RK4 engine** (`cythonized_rk4_engine`) demonstrated **the best overall performance**, being:
  - ~**7× faster** for trajectory integration  
  - ~**92× faster** for zero calculation  

- The **SciPy engine** is highly efficient, leveraging adaptive step solvers for a **4–5× speed gain** over the pure Python RK4.

- The **Euler and Verlet** engines serve as simpler, slower baselines for verification and comparison.

- The **Cythonized Euler engine** provides a **moderate boost** (~1.6× faster for trajectory, ~41× faster for zero) but remains less efficient than the RK4 variant.

---
