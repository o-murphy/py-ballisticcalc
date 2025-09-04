# Drag Models

The drag subsystem models aerodynamic resistance via standard reference tables (G1, G7, etc.) or custom Mach–CD pairs.

- `DragModel`: Single-BC scaling of a reference drag table; optional weight/diameter/length for spin-drift calculations.
- `BCPoint` + `DragModelMultiBC(...)`: Interpolate BC across velocity/Mach to better match measured data.
- Helpers: `make_data_points`, `sectional_density`, `linear_interpolation`.

Use with `Ammo(dm=DragModel(...))` to parameterize the projectile.

??? api "API Documentation"

    [`py_ballisticcalc.drag_model`][py_ballisticcalc.drag_model]<br>