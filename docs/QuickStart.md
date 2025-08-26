# QuickStart

This QuickStart gets you from a fresh environment to running basic ballistic calculations and the provided examples.

## Prerequisites
- Python 3.10+ recommended.
- A virtual environment for development (venv, conda, etc.).

## Install

- Stable (PyPI):

```bash
pip install py-ballisticcalc
```

- With native performance extensions (recommended for production/benchmarks):

```bash
pip install py-ballisticcalc[exts]
```

- From local sources (editable), useful when developing or running tests:

```bash
# from repo root
py -m pip install -e .\py_ballisticcalc.exts   # build/install C extensions (optional)
py -m pip install -e .                        # main package editable
```

## Examples

### Run a simple zero example

```python
from py_ballisticcalc import *

# create a shot with a simple DragModel
zero = Shot(weapon=Weapon(sight_height=2), ammo=Ammo(DragModel(0.22, TableG7), mv=Velocity.FPS(2600)))
calc = Calculator()
zero_distance = Distance.Yard(100)
zero_elevation = calc.set_weapon_zero(zero, zero_distance)
print(f'Barrel elevation (total): {zero_elevation}')
```

### Fire and get trajectory

```python
# fire out to 500 yards, 1 yd sampling
result = calc.fire(zero, trajectory_range=Distance.Yard(500), trajectory_step=Distance.Yard(1))
print(len(result.trajectory), "rows")
# plot if you have matplotlib
ax = result.plot()
```

## Running tests

- Install dev requirements (recommended):

```bash
py -m pip install -e .[dev]
```

- Run unit tests:

```bash
py -m pytest
```

## Files & examples
- See `examples/Examples.ipynb` and `examples/ExtremeExamples.ipynb` for notebooks demonstrating advanced usage.

## Support / Issues
- Open an issue on the GitHub repository if you encounter bugs or unexpected behavior.
