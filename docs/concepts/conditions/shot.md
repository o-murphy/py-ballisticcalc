# Shot

The [`Shot`][py_ballisticcalc.shot.Shot] class contains all information required to calculate a ballistic trajectory:

- [Atmosphere][py_ballisticcalc.conditions.Atmo] and [winds][py_ballisticcalc.conditions.Wind].
- [Ammunition][py_ballisticcalc.munition.Ammo] characteristics.
- [Gun][py_ballisticcalc.munition.Weapon] and [Sight][py_ballisticcalc.munition.Sight] characteristics.
- `look_angle` (a.k.a. _slant angle_): sight line angle relative to horizontal.
- `relative_angle` (a.k.a. _hold_): adjustment added by shooter to the gun's `zero_elevation`.
- `cant_angle`: any rotation of the sight away from vertical alignment above the gun's barrel.
- `azimuth`: Azimuth of the shooting direction in degrees [0, 360). Optional, for [Coriolis][py_ballisticcalc.conditions.Coriolis] effects.
- [`latitude`][py_ballisticcalc.shot.Shot.latitude]: Latitude of the shooting location in degrees [-90, 90]. Optional, for [Coriolis][py_ballisticcalc.conditions.Coriolis] effects.

If user supplies `latitude` and `azimuth` then engines will include [Coriolis][py_ballisticcalc.conditions.Coriolis] acceleration. If user supplies only `latitude` then a horizontal [Coriolis][py_ballisticcalc.conditions.Coriolis] approximation is applied.

???+ api "API Documentation"

    [`py_ballisticcalc.shot.Shot`][py_ballisticcalc.shot.Shot]<br>
