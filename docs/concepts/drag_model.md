## Drag Models

???+ api "API Documentation"

    [`py_ballisticcalc.drag_model`][py_ballisticcalc.drag_model]<br>

The drag subsystem models aerodynamic resistance via Ballistic Coefficients that reference standard drag tables (G1, G7, etc.), or custom Mach–$C_d$ pairs.

- [`DragModel`][py_ballisticcalc.drag_model.DragModel]: Single-BC scaling of a reference drag table; optional weight/diameter/length for spin-drift calculations.
- [`BCPoint`][py_ballisticcalc.drag_model.BCPoint] + [`DragModelMultiBC(...)`][py_ballisticcalc.drag_model.DragModelMultiBC]: Interpolate BC across velocity/Mach to better match measured data.
- Helpers: [`make_data_points`][py_ballisticcalc.drag_model.make_data_points], [`sectional_density`][py_ballisticcalc.drag_model.sectional_density], [`linear_interpolation`][py_ballisticcalc.drag_model.linear_interpolation].

Use with [`Ammo(dm=DragModel(...))`](py_ballisticcalc.munition.Ammo) to parameterize the projectile.

## Standard Models

???+ api "API Documentation"

    [`py_ballisticcalc.drag_tables`][py_ballisticcalc.drag_tables]<br>

### Standard Tables
* [`TableG1`][py_ballisticcalc.drag_tables.TableG1]: Flat-base bullet (most common sporting ammunition)
* [`TableG7`][py_ballisticcalc.drag_tables.TableG7]: Boat-tail, spitzer (long-range match bullets)
* [`TableG2`][py_ballisticcalc.drag_tables.TableG2]: Conical, banded, boat-tail artillery projectile
* [`TableG5`][py_ballisticcalc.drag_tables.TableG5]: Round-nose, boat-tail
* [`TableG6`][py_ballisticcalc.drag_tables.TableG6]: Flat-base, spire-point
* [`TableG8`][py_ballisticcalc.drag_tables.TableG8]: Flat-base, 10 caliber secant ogive
* [`TableGI`][py_ballisticcalc.drag_tables.TableGI]: Ingalls G1
* [`TableGS`][py_ballisticcalc.drag_tables.TableGS]: 9/16" smooth sphere
* [`TableRA4`][py_ballisticcalc.drag_tables.TableRA4]: .22LR 40gr

----

### Standard Projectile Profiles

![Standard Projectiles](DragModelProjectiles.jpg)

----

### Standard Drag Curves

![Standard ballistic drag curves](DragCurvesBullets.png)

