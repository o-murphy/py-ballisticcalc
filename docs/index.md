<h1 style="display: flex; align-items: center; gap: 10px;">
  <img src="./favicon.svg" alt="logo" width="50" height="50"> 
  py_ballisticcalc
</h1>

LGPL library for small arms ballistic calculations based on point-mass (3 DoF) plus spin drift.

## QuickStart

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
    pip install "py-ballisticcalc[exts]"
    ```
    
=== "uv"
    ```bash
    uv add py-ballisticcalc[exts]
    ```

- From local sources (editable), useful when developing or running tests:

=== "pip"
    ```bash
    # from repo root
    py -m pip install -e .[dev]                        # main package editable
    py -m pip install -e ./py_ballisticcalc.exts[dev]  # build/install C extensions (optional)
    ```

=== "uv"
    ```bash
    # from repo root
    uv sync                        # main package editable
    uv sync --extra exts           # build/install C extensions (optional)
    ```

## Examples

### Simple Zero

```python
from py_ballisticcalc import *

# Define a standard .308 Winchester shot: G7 BC=0.22, muzzle velocity = 2600fps
zero = Shot(weapon=Weapon(sight_height=2), ammo=Ammo(DragModel(0.22, TableG7), mv=Velocity.FPS(2600)))
calc = Calculator()
# Zero the gun for 100 yards
zero_distance = Distance.Yard(100)
zero_elevation = calc.set_weapon_zero(zero, zero_distance)
print(f'Barrel elevation for {zero_distance} zero: {zero_elevation << PreferredUnits.adjustment}')
```

    Barrel elevation for 100.0yd zero: 1.33mil

### Print Range Card

```python
# Generate Range card for this zero with a 5mph cross-wind from left to right
zero.winds = [Wind(Velocity.MPH(5), Angular.OClock(3))]
range_card = calc.fire(zero, trajectory_range=500, trajectory_step=100)
range_card.dataframe(True)[['distance', 'velocity', 'mach', 'time', 'height', 'drop_angle', 'windage', 'windage_angle']]
```

| distance  | velocity    | mach      | time    | height      | drop_angle | windage   | windage_angle |
|-----------|-------------|-----------|---------|-------------|------------|-----------|---------------|
| 0.0 yd    | 2600.0 ft/s | 2.33 mach | 0.000 s | -2.0 inch   | 0.00 mil   | -0.0 inch | 0.00 mil      |
| 100.0 yd  | 2398.1 ft/s | 2.15 mach | 0.120 s | -0.0 inch   | -0.00 mil  | 0.4 inch  | 0.12 mil      |
| 200.0 yd  | 2205.5 ft/s | 1.98 mach | 0.251 s | -4.1 inch   | -0.57 mil  | 1.7 inch  | 0.25 mil      |
| 300.0 yd  | 2022.3 ft/s | 1.81 mach | 0.393 s | -15.3 inch  | -1.44 mil  | 4.1 inch  | 0.39 mil      |
| 400.0 yd  | 1847.5 ft/s | 1.65 mach | 0.548 s | -35.0 inch  | -2.48 mil  | 7.6 inch  | 0.54 mil      |
| 500.0 yd  | 1680.1 ft/s | 1.50 mach | 0.718 s | -65.0 inch  | -3.68 mil  | 12.4 inch | 0.70 mil      |


### More Examples
See `examples/Examples.ipynb` and `examples/ExtremeExamples.ipynb` for more detailed examples.


## Support / Issues
- [Open an issue on the GitHub repository](https://github.com/o-murphy/py-ballisticcalc/issues) if you encounter bugs or unexpected behavior.
