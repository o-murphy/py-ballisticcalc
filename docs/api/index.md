# Overview

This page summarizes the primary classes you’ll use in py-ballisticcalc and how they fit together at runtime.

## Core Workflow

- [`Calculator`][py_ballisticcalc.interface.Calculator]: High-level entry point to compute trajectories. Accepts a [`Shot`][py_ballisticcalc.conditions.Shot] (scene) and returns a [`HitResult`][py_ballisticcalc.trajectory_data.HitResult] with trajectory rows and helpers.
- [`Shot`][py_ballisticcalc.conditions.Shot]: Details a shooting scenario – [`Ammo`][py_ballisticcalc.munition.Ammo], [`Weapon`][py_ballisticcalc.munition.Weapon], [`Atmo`][py_ballisticcalc.conditions.Atmo], [`Wind`][py_ballisticcalc.conditions.Wind], and angles (look/slant, relative, cant). Engines convert `Shot` to `ShotProps`.
- [`ShotProps`][py_ballisticcalc.conditions.ShotProps]: Engine-ready scalar form of `Shot` in internal units.
- [`BaseTrajData`][py_ballisticcalc.trajectory_data.BaseTrajData]: Minimal, units-free state for dense internal calculations; used to construct `TrajectoryData` via post-processing.
- [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]: Detailed characteristics of a point on the ballistic trajectory.
- [`HitResult`][py_ballisticcalc.trajectory_data.HitResult]: Wrapper for accessing and displaying calculated results.

## Projectile & Environment

The classes that comprise a [`Shot`][py_ballisticcalc.conditions.Shot]:

- [`Atmo`][py_ballisticcalc.conditions.Atmo]: Standard or custom atmosphere.
    - [`Wind`][py_ballisticcalc.conditions.Wind]: Piecewise-constant winds by distance.
- [`Ammo`][py_ballisticcalc.munition.Ammo]: Wraps projectile physical details and muzzle velocity, including optional powder temperature sensitivity.
    - [`DragModel`][py_ballisticcalc.drag_model]: Aerodynamic drag via Ballistic Coefficient and standard drag tables (G1, G7, etc.).
- [`Weapon`][py_ballisticcalc.munition.Weapon]: Gun specifications (sight height, rifle twist rate, zero elevation).

## Engines

Calculation engines implement different algorithms for integration and targeting.  All inherit from [`BaseIntegrationEngine`][py_ballisticcalc.engines.base_engine.BaseIntegrationEngine].


???+ api "Selected API references"

	[`py_ballisticcalc.interface.Calculator`][py_ballisticcalc.interface.Calculator]<br>
	[`py_ballisticcalc.conditions.Shot`][py_ballisticcalc.conditions.Shot]<br>
	[`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>
	[`py_ballisticcalc.conditions.Atmo`][py_ballisticcalc.conditions.Atmo]<br>
	[`py_ballisticcalc.munition.Weapon`][py_ballisticcalc.munition.Weapon]<br>
	[`py_ballisticcalc.trajectory_data.HitResult`][py_ballisticcalc.trajectory_data.HitResult]<br>
	[`py_ballisticcalc.trajectory_data.TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]<br>

