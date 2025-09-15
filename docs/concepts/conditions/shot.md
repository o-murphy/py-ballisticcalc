# Shot

The [`Shot`][py_ballisticcalc.conditions.Shot] class contains all information required to calculate a ballistic trajectory:

- [Atmosphere][py_ballisticcalc.conditions.Atmo] and [winds][py_ballisticcalc.conditions.Wind].
- [Ammunition][py_ballisticcalc.munition.Ammo] characteristics.
- [Gun][py_ballisticcalc.munition.Weapon] and [Sight][py_ballisticcalc.munition.Sight] characteristics.
- `look_angle` (a.k.a. _slant angle_): sight line angle relative to horizontal.
- `relative_angle` (a.k.a. _hold_): adjustment added by shooter to the gun's `zero_elevation`.
- `cant_angle`: any rotation of the sight away from vertical alignment above the gun's barrel.

???+ api "API Documentation"

    [`py_ballisticcalc.conditions.Shot`][py_ballisticcalc.conditions.Shot]<br>
