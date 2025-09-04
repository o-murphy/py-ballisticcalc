# Shot

The scene configuration for a calculation: weapon, ammo, atmosphere, winds, and angles.

- `look_angle` (a.k.a. slant angle): sight line elevation vs horizon.
- `relative_angle`: adjustment added to the weapon’s `zero_elevation`.
- `cant_angle`: rotates barrel elevation into an azimuth component.
- Derived: `barrel_elevation` and `barrel_azimuth`.

??? api "API Documentation"

    [`py_ballisticcalc.conditions.Shot`][py_ballisticcalc.conditions.Shot]<br>
