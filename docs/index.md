# py_ballisticcalc QuickStart

This QuickStart gets you from a fresh environment to running basic ballistic calculations.

## Install

**Prerequisites:** Python 3.10+.

- Latest release (PyPI):

=== "pip"
    ```bash
    pip install py-ballisticcalc
    ```
    
=== "uv"
    ```bash
    uv add py-ballisticcalc
    ```

- With performance extensions (recommended for production/benchmarks):

=== "pip"
    ```bash
    pip install py-ballisticcalc[exts]
    ```
    
=== "uv"
    ```bash
    uv add py-ballisticcalc[exts]
    ```

- From local sources (editable), useful when developing or running tests:

=== "pip"
    ```bash
    # from repo root
    py -m pip install -e .                         # main package editable
    py -m pip install -e .\py_ballisticcalc.exts   # build/install C extensions (optional)
    ```

=== "uv"
    ```bash
    # from repo root
    uv sync --dev                        # main package editable
    uv sync --dev --extra exts           # build/install C extensions (optional)
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

### More Examples
See `examples\Examples.ipynb` and `examples\ExtremeExamples.ipynb` for more detailed examples.


## Support / Issues
- [Open an issue on the GitHub repository](https://github.com/o-murphy/py-ballisticcalc/issues) if you encounter bugs or unexpected behavior.
