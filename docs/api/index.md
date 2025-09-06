# Overview

This page summarizes the primary classes you’ll use in py-ballisticcalc and how they fit together at runtime.

## Core Workflow

- [`Calculator`][py_ballisticcalc.interface.Calculator]: High-level entry point to compute trajectories. Accepts a `Shot` (scene) and returns a `HitResult` with trajectory rows and helpers.
- [`Shot`][py_ballisticcalc.conditions.Shot]: Details a shooting scenario – [`Ammo`][py_ballisticcalc.munition.Ammo], [`Weapon`][py_ballisticcalc.munition.Weapon], [`Atmo`][py_ballisticcalc.conditions.Atmo], [`Wind`][py_ballisticcalc.conditions.Wind], and angles (look/slant, relative, cant). Engines convert `Shot` to `ShotProps`.
- `ShotProps`: Engine-ready scalar form of `Shot` in internal units (ft, s, grains), with precomputed drag curve, stability, and atmosphere lookups.
- `TrajectoryData`: A human-friendly trajectory row with units (distance, height, windage, angles, energy, etc.) and flags for special events.
- `BaseTrajData`: Minimal, units-free state for dense internal stepping; used to construct `TrajectoryData` via post-processing.
- `HitResult`: Wrapper for results; provides convenience methods like `zeros()`, `get_at(...)`, `danger_space(...)`, `plot()` and `dataframe()`.

## Projectile and Environment

- `DragModel` and `DragModelMultiBC`: Aerodynamic drag via BC and standard tables (G1, G7, etc.), or multi-BC interpolation across Mach/velocity.
- `Ammo`: Wraps projectile and muzzle details, including optional powder temperature sensitivity.
- `Weapon`: Rifle setup (sight height, twist, zero elevation, sight properties).
- `Atmo`/`Vacuum`: Standard or custom atmosphere with density ratio and local Mach; supports ICAO presets and humidity.
- `Wind`: Piecewise-constant winds by range, convertible to 3D vectors for engine use.
- `Vector`: Immutable 3D vector used for position and velocity in internal calculations.

## Engines

Engines implement numeric integration (Euler, RK4, SciPy, Cythonized variants). Choose by name when creating `Calculator` or via entry points.

## Learn by Example

- Examples notebook: https://github.com/o-murphy/py_ballisticcalc/blob/main/examples/Examples.ipynb
- Slant angle walk-through: https://github.com/o-murphy/py_ballisticcalc/blob/main/examples/Understanding_Slant_Angle.ipynb

## API Pointers

??? api "Selected API references"

	[`py_ballisticcalc.interface.Calculator`][py_ballisticcalc.interface.Calculator]<br>
	[`py_ballisticcalc.conditions.Shot`][py_ballisticcalc.conditions.Shot]<br>
	[`py_ballisticcalc.conditions.Atmo`][py_ballisticcalc.conditions.Atmo]<br>
	[`py_ballisticcalc.munition.Weapon`][py_ballisticcalc.munition.Weapon]<br>
	[`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>
	[`py_ballisticcalc.drag_model.DragModel`][py_ballisticcalc.drag_model.DragModel]<br>
	[`py_ballisticcalc.trajectory_data.HitResult`][py_ballisticcalc.trajectory_data.HitResult]<br>
	[`py_ballisticcalc.trajectory_data.TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]<br>

