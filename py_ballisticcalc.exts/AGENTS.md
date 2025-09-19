# AGENTS.md

This (`py_ballisticcalc.exts`) is the optional Cython subproject of `py_ballisticcalc`. Its purpose is to provide maximum-speed engines that preserve parity with those in the root project:
* `py_ballisticcalc_exts.rk4_engine:CythonizedRK4IntegrationEngine` is high-speed version of root `RK4IntegrationEngine`. Entry-point name: `cythonized_rk4_engine` 
* `py_ballisticcalc_exts.euler_engine:CythonizedEulerIntegrationEngine` is high-speed version of root `EulerIntegrationEngine`. Entry-point name: `cythonized_euler_engine` 

**Root project `py_ballisticcalc` is source of truth for all functionality.**  However, `py_ballisticcalc_exts` code files do not necessarily map 1-to-1 with root project modules.

`py_ballisticcalc_exts` key files:
* `base_engine.pyx/pxd` and `trajectory_data.pyx/pxd` reference `py_ballisticcalc/engines/base_engine.py` and `py_ballisticcalc/trajectory_data.py`
  * `trajectory_data.pyx/pxd` is a lightweight subset of the Python types for internal use. Don't assume parity even if the names are similar.
* `rk4_engine.pyx` references `py_ballisticcalc/engines/rk4.py`
* `euler_engine.pyx` references `py_ballisticcalc/engines/euler.py`
* `base_traj_seq.pyx` provides a contiguous C buffer + interpolation without Python allocation; key APIs: `__getitem__`, `get_at()`
* `cy_bindings.pxd` provides C structs and helpers

# Testing
From subproject root, `pytest tests` only test functionality unique to Cython and this subproject.
* For coverage of Cython code, true line coverage requires compiling with CYTHON_TRACE; otherwise rely on tests passing and targeted smoke checks.

To confirm core functionality run root project tests with cythonized engines. From repo root: `pytest --engine="cythonized_rk4_engine"`

# Build/Install notes
- Use editable installs during iteration. From repo root: `pip install -e .[dev]`
- To rebuild this subproject from parent repo root: `pip install -e ./py_ballisticcalc.exts`

# Hot paths & safety
- Try to keep hot loops in nogil C math. Avoid Python object creation when scanning C buffers.
- Free all C allocations on all exit paths. E.g., `base_engine._free_trajectory()` should null out pointers/lengths.
