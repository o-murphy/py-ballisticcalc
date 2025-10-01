# Overview

This page summarizes the primary classes for this project and how they fit together at runtime.

## Core Workflow

- [`Calculator`][py_ballisticcalc.interface.Calculator]: High-level entry point to compute trajectories. Accepts a [`Shot`][py_ballisticcalc.shot.Shot] (scene) and returns a [`HitResult`][py_ballisticcalc.trajectory_data.HitResult] with trajectory rows and helpers.
- [`Shot`][py_ballisticcalc.shot.Shot]: Details a shooting scenario – [`Ammo`][py_ballisticcalc.munition.Ammo], [`Atmo`][py_ballisticcalc.conditions.Atmo], [`Weapon`][py_ballisticcalc.munition.Weapon], [`Wind`][py_ballisticcalc.conditions.Wind], and angles (look/slant, relative, cant).
- [`HitResult`][py_ballisticcalc.trajectory_data.HitResult]: Wrapper for accessing and displaying calculated results, including a list of [`TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData] (which are detailed characteristics of points on the ballistic trajectory).


## Projectile & Environment
<div style="text-align: center;">

```mermaid
classDiagram
    class Shot {
		look_angle
		relative_angle
	}
    class Ammo {
		mv
		temp_modifier
	}
    class Atmo {
		altitude
		temperature
		pressure
		humidity
	}
    class Wind
    class Weapon {
		zero_elevation
		sight_height
		twist
	}
    class DragModel
	class Sight

    Shot o-- Ammo
    Shot o-- Atmo
    Shot o-- "0..n" Wind
    Shot o-- "0..1" Weapon
    Ammo o-- DragModel
	Weapon o-- "0..1" Sight
```
</div>

The classes that comprise a [`Shot`][py_ballisticcalc.shot.Shot]:

- [`Ammo`][py_ballisticcalc.munition.Ammo]: Wraps muzzle velocity, including optional powder temperature sensitivity, together with a DragModel.
    - [`DragModel`][py_ballisticcalc.drag_model]: Physical details of a projectile, including aerodynamic drag as a function of velocity.  (Drag is typically modelled via Ballistic Coefficient and standard [drag tables][py_ballisticcalc.drag_tables] – G1, G7, etc.)
- [`Atmo`][py_ballisticcalc.conditions.Atmo]: Standard or custom atmosphere.
- [`Wind`][py_ballisticcalc.conditions.Wind]: Piecewise-constant winds by distance.
- [`Weapon`][py_ballisticcalc.munition.Weapon]: Gun specifications (sight height, rifle twist rate, zero elevation, [`Sight`][py_ballisticcalc.munition.Weapon] details).

## [Engines](../concepts/engines.md)

Calculation engines implement different algorithms for integration and targeting.  All inherit from [`BaseIntegrationEngine`][py_ballisticcalc.engines.base_engine.BaseIntegrationEngine].

- [RK4IntegrationEngine][py_ballisticcalc.engines.RK4IntegrationEngine]
- [EulerIntegrationEngine][py_ballisticcalc.engines.EulerIntegrationEngine]
- [VelocityVerletIntegrationEngine][py_ballisticcalc.engines.VelocityVerletIntegrationEngine]
- [SciPyIntegrationEngine][py_ballisticcalc.engines.SciPyIntegrationEngine]

???+ api "Selected API references"

	[`py_ballisticcalc.interface.Calculator`][py_ballisticcalc.interface.Calculator]<br>
	[`py_ballisticcalc.shot.Shot`][py_ballisticcalc.shot.Shot]<br>
	[`py_ballisticcalc.munition.Ammo`][py_ballisticcalc.munition.Ammo]<br>
	[`py_ballisticcalc.conditions.Atmo`][py_ballisticcalc.conditions.Atmo]<br>
	[`py_ballisticcalc.munition.Weapon`][py_ballisticcalc.munition.Weapon]<br>
	[`py_ballisticcalc.trajectory_data.HitResult`][py_ballisticcalc.trajectory_data.HitResult]<br>
	[`py_ballisticcalc.trajectory_data.TrajectoryData`][py_ballisticcalc.trajectory_data.TrajectoryData]<br>

